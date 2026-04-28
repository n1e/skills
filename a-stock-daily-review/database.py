#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB 数据持久化模块
用于存储和查询历史复盘数据、自选股和个股详情
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

import duckdb

from logger import logger
from models.market import MarketData, VolumeData
from models.stock import SurgeStock, CompositeHeatRank
from models.review import DailyReview


class DatabaseManager:
    """DuckDB 数据库管理器"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，默认使用 output/reviews.duckdb
        """
        if db_path is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(script_dir, 'output')
            os.makedirs(output_dir, exist_ok=True)
            db_path = os.path.join(output_dir, 'reviews.duckdb')
        
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self):
        """获取数据库连接"""
        return duckdb.connect(self.db_path)
    
    def _init_database(self):
        """初始化数据库表结构"""
        logger.info(f"初始化数据库: {self.db_path}")
        
        conn = self._get_connection()
        try:
            # 1. 每日复盘主表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_reviews (
                    date VARCHAR PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    market_data_json TEXT,
                    volume_history_json TEXT,
                    surge_stocks_json TEXT,
                    heat_ranks_json TEXT,
                    news_ranks_json TEXT
                )
            """)
            
            # 2. 自选股表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    code VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes VARCHAR
                )
            """)
            
            # 3. 个股详情表（同花顺点评和资讯）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_details (
                    code VARCHAR PRIMARY KEY,
                    name VARCHAR,
                    latest_price FLOAT,
                    change_pct FLOAT,
                    comment_json TEXT,
                    news_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 4. 涨停股票明细表（便于多日分析）
            # 使用复合主键 (date, code)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS surge_stocks_daily (
                    date VARCHAR,
                    code VARCHAR,
                    name VARCHAR,
                    price FLOAT,
                    change_pct FLOAT,
                    reason VARCHAR,
                    reason_category VARCHAR,
                    PRIMARY KEY (date, code)
                )
            """)
            
            # 5. 人气排名明细表（便于多日分析）
            # 使用复合主键 (date, code)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heat_ranks_daily (
                    date VARCHAR,
                    code VARCHAR,
                    name VARCHAR,
                    composite_score FLOAT,
                    appear_count INTEGER,
                    wencai_rank INTEGER,
                    xueqiu_rank INTEGER,
                    eastmoney_rank INTEGER,
                    thsi_rank INTEGER,
                    PRIMARY KEY (date, code)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_surge_date ON surge_stocks_daily(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_surge_code ON surge_stocks_daily(code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_heat_date ON heat_ranks_daily(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_heat_code ON heat_ranks_daily(code)")
            
            logger.info("数据库初始化完成")
        finally:
            conn.close()
    
    # ==================== 每日复盘数据操作 ====================
    
    def save_review(self, review: DailyReview) -> bool:
        """
        保存每日复盘数据
        
        Args:
            review: DailyReview 对象
            
        Returns:
            是否保存成功
        """
        conn = self._get_connection()
        try:
            # 准备JSON数据
            market_json = json.dumps({
                'date': review.market.date,
                'up_count': review.market.up_count,
                'down_count': review.market.down_count,
                'flat_count': review.market.flat_count,
                'total_count': review.market.total_count,
                'limit_up_count': review.market.limit_up_count,
                'limit_down_count': review.market.limit_down_count,
                'suspension_count': review.market.suspension_count,
                'real_limit_up_count': review.market.real_limit_up_count,
                'real_limit_down_count': review.market.real_limit_down_count,
                'fear_index': review.market.fear_index,
                'greed_index': review.market.greed_index,
                'congestion': review.market.congestion,
                'up_0_3': review.market.up_0_3,
                'up_3_5': review.market.up_3_5,
                'up_5_7': review.market.up_5_7,
                'up_7_10': review.market.up_7_10,
                'up_10_20': review.market.up_10_20,
                'down_0_3': review.market.down_0_3,
                'down_3_5': review.market.down_3_5,
                'down_5_7': review.market.down_5_7,
                'down_7_10': review.market.down_7_10,
                'down_10_20': review.market.down_10_20,
            }, ensure_ascii=False)
            
            volume_json = json.dumps([
                {'date': v.date, 'volume': v.volume} 
                for v in review.volume_history
            ], ensure_ascii=False)
            
            surge_json = json.dumps([
                {
                    'code': s.code, 'name': s.name, 
                    'price': s.price, 'change_pct': s.change_pct,
                    'reason': s.reason, 'reason_category': s.reason_category
                } 
                for s in review.surge_stocks
            ], ensure_ascii=False)
            
            heat_json = json.dumps([
                {
                    'code': h.code, 'name': h.name,
                    'wencai_rank': h.wencai_rank, 'xueqiu_rank': h.xueqiu_rank,
                    'eastmoney_rank': h.eastmoney_rank, 'thsi_rank': h.thsi_rank,
                    'composite_score': h.composite_score, 'appear_count': h.appear_count
                } 
                for h in review.heat_ranks
            ], ensure_ascii=False)
            
            news_json = json.dumps([
                {
                    'title': n.title, 'source': n.source,
                    'url': n.url, 'heat_score': n.heat_score if hasattr(n, 'heat_score') else 0
                } 
                for n in review.news_ranks
            ], ensure_ascii=False)
            
            # 插入或更新主表
            conn.execute("""
                INSERT OR REPLACE INTO daily_reviews 
                (date, created_at, market_data_json, volume_history_json, 
                 surge_stocks_json, heat_ranks_json, news_ranks_json)
                VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            """, [review.date, market_json, volume_json, surge_json, heat_json, news_json])
            
            # 保存到明细表（便于多日分析）
            self._save_surge_stocks_detail(conn, review.date, review.surge_stocks)
            self._save_heat_ranks_detail(conn, review.date, review.heat_ranks)
            
            conn.commit()
            logger.info(f"复盘数据已保存到数据库: {review.date}")
            return True
            
        except Exception as e:
            logger.error(f"保存复盘数据失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _save_surge_stocks_detail(self, conn, date: str, stocks: List[SurgeStock]):
        """保存涨停股票到明细表"""
        for stock in stocks:
            conn.execute("""
                INSERT OR REPLACE INTO surge_stocks_daily 
                (date, code, name, price, change_pct, reason, reason_category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [date, stock.code, stock.name, stock.price, 
                  stock.change_pct, stock.reason, stock.reason_category])
    
    def _save_heat_ranks_detail(self, conn, date: str, ranks: List[CompositeHeatRank]):
        """保存人气排名到明细表"""
        for rank in ranks:
            conn.execute("""
                INSERT OR REPLACE INTO heat_ranks_daily 
                (date, code, name, composite_score, appear_count,
                 wencai_rank, xueqiu_rank, eastmoney_rank, thsi_rank)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [date, rank.code, rank.name, rank.composite_score, rank.appear_count,
                  rank.wencai_rank, rank.xueqiu_rank, rank.eastmoney_rank, rank.thsi_rank])
    
    def get_review(self, date: str) -> Optional[DailyReview]:
        """
        获取指定日期的复盘数据
        
        Args:
            date: 日期字符串，格式 YYYY-MM-DD
            
        Returns:
            DailyReview 对象，不存在返回 None
        """
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT date, market_data_json, volume_history_json,
                       surge_stocks_json, heat_ranks_json, news_ranks_json
                FROM daily_reviews
                WHERE date = ?
            """, [date]).fetchone()
            
            if not result:
                return None
            
            review = DailyReview()
            review.date = result[0]
            
            # 解析市场数据
            if result[1]:
                market_data = json.loads(result[1])
                review.market = MarketData()
                review.market.date = market_data.get('date', '')
                review.market.up_count = market_data.get('up_count', 0)
                review.market.down_count = market_data.get('down_count', 0)
                review.market.flat_count = market_data.get('flat_count', 0)
                review.market.total_count = market_data.get('total_count', 0)
                review.market.limit_up_count = market_data.get('limit_up_count', 0)
                review.market.limit_down_count = market_data.get('limit_down_count', 0)
                review.market.suspension_count = market_data.get('suspension_count', 0)
                review.market.real_limit_up_count = market_data.get('real_limit_up_count', 0)
                review.market.real_limit_down_count = market_data.get('real_limit_down_count', 0)
                review.market._fear_index = market_data.get('fear_index', -1)
                review.market._greed_index = market_data.get('greed_index', -1)
                review.market._congestion = market_data.get('congestion', -1)
                review.market.up_0_3 = market_data.get('up_0_3', 0)
                review.market.up_3_5 = market_data.get('up_3_5', 0)
                review.market.up_5_7 = market_data.get('up_5_7', 0)
                review.market.up_7_10 = market_data.get('up_7_10', 0)
                review.market.up_10_20 = market_data.get('up_10_20', 0)
                review.market.down_0_3 = market_data.get('down_0_3', 0)
                review.market.down_3_5 = market_data.get('down_3_5', 0)
                review.market.down_5_7 = market_data.get('down_5_7', 0)
                review.market.down_7_10 = market_data.get('down_7_10', 0)
                review.market.down_10_20 = market_data.get('down_10_20', 0)
            
            # 解析成交量历史
            if result[2]:
                volume_list = json.loads(result[2])
                review.volume_history = [
                    VolumeData(date=v['date'], volume=v['volume']) 
                    for v in volume_list
                ]
            
            # 解析涨停股票
            if result[3]:
                surge_list = json.loads(result[3])
                review.surge_stocks = [
                    SurgeStock(
                        code=s['code'], name=s['name'],
                        price=s['price'], change_pct=s['change_pct'],
                        reason=s['reason'], reason_category=s['reason_category']
                    ) 
                    for s in surge_list
                ]
            
            # 解析人气排名
            if result[4]:
                heat_list = json.loads(result[4])
                review.heat_ranks = [
                    CompositeHeatRank(
                        code=h['code'], name=h['name'],
                        wencai_rank=h['wencai_rank'], xueqiu_rank=h['xueqiu_rank'],
                        eastmoney_rank=h['eastmoney_rank'], thsi_rank=h['thsi_rank'],
                        composite_score=h['composite_score'], appear_count=h['appear_count']
                    ) 
                    for h in heat_list
                ]
            
            # 解析新闻排名（简化处理）
            if result[5]:
                from models.news import CompositeNewsRank
                news_list = json.loads(result[5])
                review.news_ranks = []
                for n in news_list:
                    nr = CompositeNewsRank()
                    nr.title = n.get('title', '')
                    nr.source = n.get('source', '')
                    nr.url = n.get('url', '')
                    review.news_ranks.append(nr)
            
            return review
            
        except Exception as e:
            logger.error(f"获取复盘数据失败: {e}")
            return None
        finally:
            conn.close()
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的复盘日期列表
        
        Returns:
            日期列表，按降序排列
        """
        conn = self._get_connection()
        try:
            results = conn.execute("""
                SELECT date FROM daily_reviews ORDER BY date DESC
            """).fetchall()
            return [r[0] for r in results]
        except Exception as e:
            logger.error(f"获取可用日期失败: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== 多日数据分析接口 ====================
    
    def get_stock_surge_history(self, code: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取某只股票的涨停历史
        
        Args:
            code: 股票代码
            days: 查询天数
            
        Returns:
            涨停历史列表
        """
        conn = self._get_connection()
        try:
            results = conn.execute("""
                SELECT date, code, name, price, change_pct, reason, reason_category
                FROM surge_stocks_daily
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """, [code, days]).fetchall()
            
            return [
                {
                    'date': r[0], 'code': r[1], 'name': r[2],
                    'price': r[3], 'change_pct': r[4],
                    'reason': r[5], 'reason_category': r[6]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"获取股票涨停历史失败: {e}")
            return []
        finally:
            conn.close()
    
    def get_stock_heat_history(self, code: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        获取某只股票的人气排名历史
        
        Args:
            code: 股票代码
            days: 查询天数
            
        Returns:
            人气排名历史列表
        """
        conn = self._get_connection()
        try:
            results = conn.execute("""
                SELECT date, code, name, composite_score, appear_count,
                       wencai_rank, xueqiu_rank, eastmoney_rank, thsi_rank
                FROM heat_ranks_daily
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """, [code, days]).fetchall()
            
            return [
                {
                    'date': r[0], 'code': r[1], 'name': r[2],
                    'composite_score': r[3], 'appear_count': r[4],
                    'wencai_rank': r[5], 'xueqiu_rank': r[6],
                    'eastmoney_rank': r[7], 'thsi_rank': r[8]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"获取股票人气历史失败: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== 自选股操作 ====================
    
    def add_to_watchlist(self, code: str, name: str = "", notes: str = "") -> bool:
        """
        添加股票到自选股
        
        Args:
            code: 股票代码
            name: 股票名称
            notes: 备注
            
        Returns:
            是否添加成功
        """
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO watchlist (code, name, added_at, notes)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?)
            """, [code, name, notes])
            conn.commit()
            logger.info(f"已添加到自选股: {code} - {name}")
            return True
        except Exception as e:
            logger.error(f"添加自选股失败: {e}")
            return False
        finally:
            conn.close()
    
    def batch_add_watchlist(self, stocks: List[Dict[str, str]]) -> int:
        """
        批量添加自选股
        
        Args:
            stocks: 股票列表，每项包含 code 和可选的 name、notes
            
        Returns:
            成功添加的数量
        """
        count = 0
        for stock in stocks:
            if self.add_to_watchlist(
                stock['code'], 
                stock.get('name', ''), 
                stock.get('notes', '')
            ):
                count += 1
        return count
    
    def remove_from_watchlist(self, code: str) -> bool:
        """
        从自选股移除
        
        Args:
            code: 股票代码
            
        Returns:
            是否移除成功
        """
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM watchlist WHERE code = ?", [code])
            conn.commit()
            logger.info(f"已从自选股移除: {code}")
            return True
        except Exception as e:
            logger.error(f"移除自选股失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_watchlist(self) -> List[Dict[str, Any]]:
        """
        获取自选股列表
        
        Returns:
            自选股列表
        """
        conn = self._get_connection()
        try:
            results = conn.execute("""
                SELECT code, name, added_at, notes
                FROM watchlist ORDER BY added_at DESC
            """).fetchall()
            
            return [
                {
                    'code': r[0], 'name': r[1],
                    'added_at': str(r[2]), 'notes': r[3]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"获取自选股失败: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== 个股详情操作 ====================
    
    def save_stock_detail(self, code: str, name: str, latest_price: float, 
                          change_pct: float, comment: Dict = None, 
                          news: List[Dict] = None) -> bool:
        """
        保存个股详情（同花顺点评和资讯）
        
        Args:
            code: 股票代码
            name: 股票名称
            latest_price: 最新价
            change_pct: 涨跌幅
            comment: 点评数据字典
            news: 资讯列表
            
        Returns:
            是否保存成功
        """
        conn = self._get_connection()
        try:
            comment_json = json.dumps(comment, ensure_ascii=False) if comment else '{}'
            news_json = json.dumps(news, ensure_ascii=False) if news else '[]'
            
            conn.execute("""
                INSERT OR REPLACE INTO stock_details 
                (code, name, latest_price, change_pct, comment_json, news_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [code, name, latest_price, change_pct, comment_json, news_json])
            conn.commit()
            logger.info(f"个股详情已保存: {code} - {name}")
            return True
        except Exception as e:
            logger.error(f"保存个股详情失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_stock_detail(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取个股详情
        
        Args:
            code: 股票代码
            
        Returns:
            个股详情字典，不存在返回 None
        """
        conn = self._get_connection()
        try:
            result = conn.execute("""
                SELECT code, name, latest_price, change_pct, comment_json, news_json, updated_at
                FROM stock_details WHERE code = ?
            """, [code]).fetchone()
            
            if not result:
                return None
            
            comment = json.loads(result[4]) if result[4] else {}
            news = json.loads(result[5]) if result[5] else []
            
            return {
                'code': result[0],
                'name': result[1],
                'latest_price': result[2],
                'change_pct': result[3],
                'comment': comment,
                'news': news,
                'updated_at': str(result[6])
            }
        except Exception as e:
            logger.error(f"获取个股详情失败: {e}")
            return None
        finally:
            conn.close()


# 全局数据库实例
_db_instance: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
