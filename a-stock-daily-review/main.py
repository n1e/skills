#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股每日复盘技能 - 主程序
每天下午4点运行，生成A股每日复盘报告
数据来源：问财 + 雪球 + 东方财富
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config
from logger import setup_logger, logger
from models.market import MarketData
from models.stock import SurgeStock, CompositeHeatRank, HeatRank
from models.review import DailyReview
from fetcher.wencai import WencaiFetcher
from fetcher.xueqiu import XueqiuFetcher
from fetcher.eastmoney import EastmoneyFetcher
from fetcher.legu import LeguFetcher
from fetcher.funddb import FunddbFetcher
from fetcher.akshare_fetcher import AKShareFetcher
from analyzer.reason_analyzer import ReasonAnalyzer
from analyzer.heat_ranker import HeatRanker
from reporter.generators import MarkdownGenerator, JsonGenerator, PDFGenerator, HTMLGenerator


def collect_market_data(legu_fetcher: LeguFetcher) -> MarketData:
    """
    收集大盘数据（从乐股获取）
    
    Args:
        legu_fetcher: 乐股采集器实例
        
    Returns:
        大盘数据对象
    """
    logger.info("开始收集大盘数据（乐股）")
    market = MarketData()
    
    # 从乐股获取数据（涨跌统计、拥挤度、涨跌分布等）
    try:
        logger.info("尝试从乐股获取市场数据...")
        legu_data = legu_fetcher.get_all_market_data()
        
        if legu_data:
            market.up_count = int(legu_data.get('up_count', legu_data.get('rise_count', 0)))
            market.down_count = int(legu_data.get('down_count', legu_data.get('fall_count', 0)))
            market.flat_count = int(legu_data.get('flat_count', 0))
            market.limit_up_count = int(legu_data.get('limit_up_count', 0))
            market.limit_down_count = int(legu_data.get('limit_down_count', 0))
            market.suspension_count = int(legu_data.get('suspension_count', 0))
            market.real_limit_up_count = int(legu_data.get('real_limit_up_count', legu_data.get('real_raising_limit_count', 0)))
            market.real_limit_down_count = int(legu_data.get('real_limit_down_count', 0))
            
            # 计算总家数（上涨+下跌+平盘）
            market.total_count = market.up_count + market.down_count + market.flat_count
            
            # 涨跌分布
            market.up_0_3 = int(legu_data.get('up_0_3', 0))
            market.up_3_5 = int(legu_data.get('up_3_5', 0))
            market.up_5_7 = int(legu_data.get('up_5_7', 0))
            market.up_7_10 = int(legu_data.get('up_7_10', 0))
            market.up_10_20 = int(legu_data.get('up_10_20', 0))
            market.down_0_3 = int(legu_data.get('down_0_3', 0))
            market.down_3_5 = int(legu_data.get('down_3_5', 0))
            market.down_5_7 = int(legu_data.get('down_5_7', 0))
            market.down_7_10 = int(legu_data.get('down_7_10', 0))
            market.down_10_20 = int(legu_data.get('down_10_20', 0))
            market.limit_up_count = int(legu_data.get('limit_up_count', 0))
            market.limit_down_count = int(legu_data.get('limit_down_count', 0))
            market.suspension_count = int(legu_data.get('suspension_count', 0))
            market.real_limit_up_count = int(legu_data.get('real_limit_up_count', legu_data.get('real_raising_limit_count', 0)))
            market.real_limit_down_count = int(legu_data.get('real_limit_down_count', legu_data.get('real_limit_down_count', 0)))
            
            # 涨跌分布
            market.up_0_3 = int(legu_data.get('up_0_3', 0))
            market.up_3_5 = int(legu_data.get('up_3_5', 0))
            market.up_5_7 = int(legu_data.get('up_5_7', 0))
            market.up_7_10 = int(legu_data.get('up_7_10', 0))
            market.up_10_20 = int(legu_data.get('up_10_20', 0))
            market.down_0_3 = int(legu_data.get('down_0_3', 0))
            market.down_3_5 = int(legu_data.get('down_3_5', 0))
            market.down_5_7 = int(legu_data.get('down_5_7', 0))
            market.down_7_10 = int(legu_data.get('down_7_10', 0))
            market.down_10_20 = int(legu_data.get('down_10_20', 0))
            
            # 大盘拥挤度（从乐股获取，格式为 "拥挤度: 43.92%"）
            congestion_str = legu_data.get('congestion', '')
            if congestion_str:
                import re
                match = re.search(r'(\d+\.?\d*)', congestion_str)
                if match:
                    market._congestion = float(match.group(1))
                    logger.info(f"大盘拥挤度: {market._congestion:.2f}%")
            
            logger.info(f"乐股市场数据获取成功: 上涨{market.up_count}, 下跌{market.down_count}")
            
            # 获取恐惧贪婪指数（从乐股数据计算）
            try:
                funddb_fetcher = FunddbFetcher()
                fear_greed_data = funddb_fetcher.get_latest_fear_greed("上证指数")
                if fear_greed_data:
                    market.fear_index = fear_greed_data.fear_index
                    market.greed_index = 100 - fear_greed_data.fear_index
                    logger.info(f"恐惧贪婪指数: 恐惧={market.fear_index:.1f}, 贪婪={market.greed_index:.1f}")
            except Exception as e:
                logger.error(f"获取恐惧贪婪指数失败: {e}")
            
            # 获取市场新闻情绪指标（从akshare获取）
            # 注：akshare接口依赖国内数据源，可能受网络环境影响
            # try:
            #     akshare_fetcher = AKShareFetcher()
            #     sentiment_data = akshare_fetcher.get_news_sentiment()
            #     if sentiment_data:
            #         market.news_sentiment_index = sentiment_data['sentiment_index']
            #         logger.info(f"市场新闻情绪指标: {market.news_sentiment_index:.4f}")
            # except Exception as e:
            #     logger.error(f"获取市场新闻情绪指标失败: {e}")
        else:
            logger.warning("乐股市场数据获取失败")
    except Exception as e:
        logger.error(f"乐股数据获取失败: {e}")
    
    logger.info(f"大盘数据收集完成: 上涨{market.up_count}, 下跌{market.down_count}, "
                f"涨停{market.limit_up_count}, 真实涨停{market.real_limit_up_count}")
    return market


def collect_volume_history(fetcher: WencaiFetcher, days: int = 30):
    """
    收集成交量历史数据
    
    Args:
        fetcher: 问财采集器实例
        days: 天数
        
    Returns:
        成交量数据列表
    """
    logger.info(f"开始收集最近{days}日成交量数据")
    volumes = fetcher.get_volume_history(days)
    logger.info(f"成交量历史数据收集完成: {len(volumes)}条记录")
    return volumes


def collect_surge_stocks(fetcher: WencaiFetcher, min_change: float = 9.5, max_stocks: int = 200):
    """
    收集涨停股票
    
    Args:
        fetcher: 问财采集器实例
        min_change: 最小涨幅阈值
        max_stocks: 最大获取数量
        
    Returns:
        涨停股票列表
    """
    logger.info(f"开始收集涨停股票（涨幅>={min_change}%）")
    stocks = fetcher.get_surge_stocks(min_change=min_change, max_stocks=max_stocks)
    logger.info(f"涨停股票收集完成: {len(stocks)}只")
    return stocks


def collect_heat_ranks(top: int = 50):
    """
    收集人气排名（多数据源：问财+雪球+东财）
    注：问财就是同花顺的数据，不需要单独调用同花顺接口
    
    Args:
        top: 获取排名数量
        
    Returns:
        (问财排名, 雪球排名, 东财排名) 元组
    """
    logger.info(f"开始收集人气排名TOP{top}")
    
    # 问财人气排名（问财=同花顺数据）
    wencai_ranks = []
    try:
        wencai_fetcher = WencaiFetcher()
        wencai_ranks = wencai_fetcher.get_heat_rank(top)
        logger.info(f"问财人气排名: {len(wencai_ranks)}只")
    except Exception as e:
        logger.error(f"问财人气排名收集失败: {e}")
    
    # 雪球热榜
    xueqiu_ranks = []
    try:
        xueqiu_fetcher = XueqiuFetcher()
        xueqiu_ranks = xueqiu_fetcher.fetch(top)
        logger.info(f"雪球热榜: {len(xueqiu_ranks)}只")
    except Exception as e:
        logger.error(f"雪球热榜收集失败: {e}")
    
    # 东财人气排名
    eastmoney_ranks = []
    try:
        eastmoney_fetcher = EastmoneyFetcher()
        eastmoney_ranks = eastmoney_fetcher.fetch(top)
        logger.info(f"东财人气排名: {len(eastmoney_ranks)}只")
    except Exception as e:
        logger.error(f"东财人气排名收集失败: {e}")
    
    return wencai_ranks, xueqiu_ranks, eastmoney_ranks


def build_review_data(date: str) -> DailyReview:
    """
    构建完整的复盘数据
    
    Args:
        date: 复盘日期
        
    Returns:
        DailyReview对象
    """
    logger.info("=" * 60)
    logger.info(f"开始构建复盘数据 - {date}")
    logger.info("=" * 60)
    
    review = DailyReview()
    review.date = date
    
    # 从配置读取参数
    min_change = config.get('surge.min_change_pct', 9.5)
    max_stocks = config.get('surge.max_stocks', 200)
    top_rank = config.get('heat_rank.top', 50)
    
    # 1. 收集大盘数据
    logger.info("\n[1/4] 收集大盘数据")
    wencai_fetcher = WencaiFetcher()
    legu_fetcher = LeguFetcher()
    review.market = collect_market_data(legu_fetcher)
    
    # 2. 收集成交量历史
    logger.info("\n[2/4] 收集成交量历史")
    review.volume_history = collect_volume_history(wencai_fetcher, days=30)
    
    # 3. 收集涨停股票
    logger.info("\n[3/4] 收集涨停股票")
    review.surge_stocks = collect_surge_stocks(wencai_fetcher, min_change, max_stocks)
    
    # 4. 收集人气排名（整合雪球、东财、问财三大平台的综合排名TOP50）
    logger.info("\n[4/4] 收集人气排名（整合雪球、东财、问财三大平台）")
    wencai_ranks, xueqiu_ranks, eastmoney_ranks = collect_heat_ranks(top_rank)
    review.heat_ranks = HeatRanker.calculate_composite_heat(
        thsi_ranks=wencai_ranks,
        xueqiu_ranks=xueqiu_ranks,
        eastmoney_ranks=eastmoney_ranks,
        top=top_rank,
        wencai_ranks=wencai_ranks
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("复盘数据构建完成!")
    logger.info(f"大盘: 涨跌比={review.market.rise_fall_ratio:.2f}, 涨停{review.market.limit_up_count}只")
    logger.info(f"涨停股票: {len(review.surge_stocks)}只")
    logger.info(f"人气排名TOP50: 已计算")
    logger.info("=" * 60)
    
    return review


def generate_report(review: DailyReview, output_format: str = 'md', output_path: str = None) -> str:
    """
    生成复盘报告
    
    Args:
        review: 复盘数据对象
        output_format: 输出格式 ('md', 'json' 或 'pdf')
        output_path: 输出文件路径（可选）
        
    Returns:
        生成的报告内容（PDF格式返回文件路径）
    """
    logger.info(f"\n生成{output_format.upper()}格式报告...")
    
    output_dir = config.get('output_dir', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    if output_format == 'pdf':
        from reporter.generators import PDFGenerator
        generator = PDFGenerator(output_dir)
        final_path = generator.generate(review)
        logger.info(f"PDF报告已生成: {final_path}")
        return final_path
    elif output_format == 'html':
        from reporter.generators import HTMLGenerator
        generator = HTMLGenerator(review)
        content = generator.generate()
        filename = f"review_{review.date}.html"
        final_path = os.path.join(output_dir, filename)
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"HTML报告已生成: {final_path}")
        return content
    elif output_format == 'json':
        generator = JsonGenerator(review)
    else:
        generator = MarkdownGenerator(review)
    
    content = generator.generate()
    
    # 确定输出路径
    if output_path:
        final_path = output_path
    else:
        filename = f"review_{review.date}.{output_format}"
        final_path = os.path.join(output_dir, filename)
    
    # 写入文件
    with open(final_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"报告已生成: {final_path}")
    return content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股每日复盘报告生成器')
    parser.add_argument('--format', choices=['md', 'json', 'pdf', 'html'], default='md',
                       help='输出格式 (默认: md)')
    parser.add_argument('--output', type=str, default='',
                       help='输出文件路径 (默认: output/review_YYYY-MM-DD.md)')
    parser.add_argument('--date', type=str, default='',
                       help='复盘日期 (格式: YYYY-MM-DD, 默认今天)')
    parser.add_argument('--debug', action='store_true',
                       help='启用调试日志')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(level=log_level)
    
    logger.info("=" * 60)
    logger.info("A股每日复盘报告生成器启动")
    logger.info("=" * 60)
    
    try:
        # 确定复盘日期
        if args.date:
            review_date = args.date
        else:
            review_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"复盘日期: {review_date}")
        
        # 构建复盘数据
        review = build_review_data(review_date)
        
        # 生成报告
        content = generate_report(review, args.format, args.output)
        
        # 输出到控制台（摘要）
        logger.info("\n报告摘要:")
        logger.info("-" * 40)
        for line in content.split('\n')[:20]:
            logger.info(line)
        if len(content.split('\n')) > 20:
            logger.info("... (更多内容已输出到文件)")
        
        logger.info("\n复盘完成!")
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断操作")
        return 130
    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    import logging
    sys.exit(main())