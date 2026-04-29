#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web服务模块
提供历史报表查询、自选股管理、个股详情展示等Web功能
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for

from logger import logger
from database import get_database
from fetcher.hexin_analyzer import HexinStockAnalyzer, get_stock_detail


class WebApp:
    """
    Web应用类
    封装Flask应用和路由
    """
    
    def __init__(self, debug: bool = False):
        """
        初始化Web应用
        
        Args:
            debug: 是否启用调试模式
        """
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                         static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        self.app.debug = debug
        self.db = get_database()
        self.stock_analyzer = HexinStockAnalyzer()
        
        self._register_routes()
    
    def _register_routes(self):
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """首页"""
            # 获取可用的日期列表
            dates = self.db.get_available_dates()
            
            # 获取最新的复盘数据
            latest_review = None
            if dates:
                latest_review = self.db.get_review(dates[0])
            
            # 获取自选股列表
            watchlist = self.db.get_watchlist()
            
            return render_template('index.html',
                                   dates=dates,
                                   latest_review=latest_review,
                                   watchlist=watchlist,
                                   now=datetime.now())
        
        @self.app.route('/review/<date>')
        def review_detail(date):
            """查看指定日期的复盘报告"""
            review = self.db.get_review(date)
            if not review:
                return f"未找到日期 {date} 的复盘数据", 404
            
            # 获取可用的日期列表用于导航
            dates = self.db.get_available_dates()
            
            return render_template('review_detail.html',
                                   review=review,
                                   dates=dates)
        
        @self.app.route('/api/reviews')
        def api_reviews():
            """API: 获取历史复盘日期列表"""
            dates = self.db.get_available_dates()
            return jsonify({
                'success': True,
                'dates': dates,
                'count': len(dates)
            })
        
        @self.app.route('/api/review/<date>')
        def api_review_detail(date):
            """API: 获取指定日期的复盘数据"""
            review = self.db.get_review(date)
            if not review:
                return jsonify({
                    'success': False,
                    'message': f'未找到日期 {date} 的复盘数据'
                }), 404
            
            # 构造响应数据
            result = {
                'success': True,
                'date': review.date,
                'market': {
                    'up_count': review.market.up_count,
                    'down_count': review.market.down_count,
                    'flat_count': review.market.flat_count,
                    'limit_up_count': review.market.limit_up_count,
                    'limit_down_count': review.market.limit_down_count,
                    'fear_index': review.market.fear_index,
                    'greed_index': review.market.greed_index,
                    'congestion': review.market.congestion,
                },
                'surge_stocks': [
                    {
                        'code': s.code,
                        'name': s.name,
                        'price': s.price,
                        'change_pct': s.change_pct,
                        'reason': s.reason,
                        'reason_category': s.reason_category
                    }
                    for s in review.surge_stocks
                ],
                'heat_ranks': [
                    {
                        'code': h.code,
                        'name': h.name,
                        'composite_score': h.composite_score,
                        'appear_count': h.appear_count
                    }
                    for h in review.heat_ranks
                ],
                'news_ranks': [
                    {
                        'title': n.title,
                        'source_count': n.source_count,
                        'composite_score': n.composite_score
                    }
                    for n in review.news_ranks
                ]
            }
            
            return jsonify(result)
        
        @self.app.route('/watchlist')
        def watchlist_page():
            """自选股页面"""
            watchlist = self.db.get_watchlist()
            
            # 获取每只股票的详细信息
            watchlist_with_detail = []
            for stock in watchlist:
                detail = self.db.get_stock_detail(stock['code'])
                watchlist_with_detail.append({
                    'code': stock['code'],
                    'name': stock['name'] or (detail.get('name', '') if detail else ''),
                    'latest_price': detail.get('latest_price', 0) if detail else 0,
                    'change_pct': detail.get('change_pct', 0) if detail else 0,
                    'added_at': stock.get('added_at', ''),
                    'notes': stock.get('notes', '')
                })
            
            dates = self.db.get_available_dates()
            
            return render_template('watchlist.html',
                                   watchlist=watchlist_with_detail,
                                   dates=dates)
        
        @self.app.route('/api/watchlist', methods=['GET'])
        def api_watchlist():
            """API: 获取自选股列表"""
            watchlist = self.db.get_watchlist()
            
            # 补充详细信息
            result = []
            for stock in watchlist:
                detail = self.db.get_stock_detail(stock['code'])
                result.append({
                    'code': stock['code'],
                    'name': stock['name'] or (detail.get('name', '') if detail else ''),
                    'latest_price': detail.get('latest_price', 0) if detail else 0,
                    'change_pct': detail.get('change_pct', 0) if detail else 0,
                    'comment': detail.get('comment', {}) if detail else {},
                    'news': detail.get('news', []) if detail else [],
                    'added_at': stock.get('added_at', ''),
                    'notes': stock.get('notes', '')
                })
            
            return jsonify({
                'success': True,
                'watchlist': result,
                'count': len(result)
            })
        
        @self.app.route('/api/watchlist', methods=['POST'])
        def api_add_watchlist():
            """API: 添加自选股"""
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': '缺少请求数据'
                }), 400
            
            code = data.get('code', '').strip()
            if not code:
                return jsonify({
                    'success': False,
                    'message': '股票代码不能为空'
                }), 400
            
            name = data.get('name', '').strip()
            notes = data.get('notes', '').strip()
            
            success = self.db.add_to_watchlist(code, name, notes)
            
            if success:
                # 尝试获取并保存个股详情
                try:
                    detail = get_stock_detail(code)
                    if detail:
                        self.db.save_stock_detail(
                            code=code,
                            name=detail.get('name', name),
                            latest_price=detail.get('latest_price', 0),
                            change_pct=detail.get('change_pct', 0),
                            comment=detail.get('comment'),
                            news=detail.get('news')
                        )
                except Exception as e:
                    logger.warning(f"获取个股详情失败: {e}")
                
                return jsonify({
                    'success': True,
                    'message': f'已添加 {code} 到自选股'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '添加失败'
                }), 500
        
        @self.app.route('/api/watchlist/batch', methods=['POST'])
        def api_batch_add_watchlist():
            """API: 批量添加自选股"""
            data = request.get_json()
            if not data or 'stocks' not in data:
                return jsonify({
                    'success': False,
                    'message': '缺少股票列表'
                }), 400
            
            stocks = data['stocks']
            if not isinstance(stocks, list):
                return jsonify({
                    'success': False,
                    'message': '股票列表格式错误'
                }), 400
            
            count = self.db.batch_add_watchlist(stocks)
            
            # 对于每只股票，尝试获取并保存个股详情（包括名称）
            success_with_detail = 0
            for stock in stocks:
                code = stock.get('code', '').strip()
                if not code:
                    continue
                
                try:
                    detail = get_stock_detail(code)
                    if detail:
                        # 使用获取到的名称，或者用户提供的名称
                        name = detail.get('name', '') or stock.get('name', '')
                        self.db.save_stock_detail(
                            code=code,
                            name=name,
                            latest_price=detail.get('latest_price', 0),
                            change_pct=detail.get('change_pct', 0),
                            comment=detail.get('comment'),
                            news=detail.get('news')
                        )
                        success_with_detail += 1
                except Exception as e:
                    logger.warning(f"批量添加时获取股票 {code} 详情失败: {e}")
            
            return jsonify({
                'success': True,
                'added_count': count,
                'with_detail_count': success_with_detail,
                'total_count': len(stocks),
                'message': f'成功添加 {count} 只股票'
            })
        
        @self.app.route('/api/watchlist/<code>', methods=['DELETE'])
        def api_remove_watchlist(code):
            """API: 从自选股移除"""
            success = self.db.remove_from_watchlist(code)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'已从自选股移除 {code}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '移除失败'
                }), 500
        
        @self.app.route('/stock/<code>')
        def stock_detail_page(code):
            """个股详情页面"""
            # 先从数据库获取
            detail = self.db.get_stock_detail(code)
            
            # 如果数据库没有或数据较旧，尝试从网络获取
            if not detail:
                try:
                    fresh_detail = get_stock_detail(code)
                    if fresh_detail:
                        self.db.save_stock_detail(
                            code=code,
                            name=fresh_detail.get('name', ''),
                            latest_price=fresh_detail.get('latest_price', 0),
                            change_pct=fresh_detail.get('change_pct', 0),
                            comment=fresh_detail.get('comment'),
                            news=fresh_detail.get('news')
                        )
                        detail = self.db.get_stock_detail(code)
                except Exception as e:
                    logger.error(f"获取个股详情失败: {e}")
            
            # 获取历史数据（涨停历史、人气排名历史）
            surge_history = self.db.get_stock_surge_history(code, days=30)
            heat_history = self.db.get_stock_heat_history(code, days=30)
            
            # 获取可用日期列表
            dates = self.db.get_available_dates()
            
            return render_template('stock_detail.html',
                                   code=code,
                                   detail=detail,
                                   surge_history=surge_history,
                                   heat_history=heat_history,
                                   dates=dates)
        
        @self.app.route('/api/stock/<code>')
        def api_stock_detail(code):
            """API: 获取个股详情"""
            # 先从数据库获取
            detail = self.db.get_stock_detail(code)
            
            # 如果数据库没有，尝试从网络获取
            if not detail:
                try:
                    fresh_detail = get_stock_detail(code)
                    if fresh_detail:
                        self.db.save_stock_detail(
                            code=code,
                            name=fresh_detail.get('name', ''),
                            latest_price=fresh_detail.get('latest_price', 0),
                            change_pct=fresh_detail.get('change_pct', 0),
                            comment=fresh_detail.get('comment'),
                            news=fresh_detail.get('news')
                        )
                        detail = self.db.get_stock_detail(code)
                except Exception as e:
                    logger.error(f"获取个股详情失败: {e}")
            
            if not detail:
                return jsonify({
                    'success': False,
                    'message': f'未找到股票 {code} 的详情'
                }), 404
            
            # 获取历史数据
            surge_history = self.db.get_stock_surge_history(code, days=30)
            heat_history = self.db.get_stock_heat_history(code, days=30)
            
            return jsonify({
                'success': True,
                'detail': detail,
                'surge_history': surge_history,
                'heat_history': heat_history
            })
        
        @self.app.route('/api/stock/<code>/refresh')
        def api_refresh_stock_detail(code):
            """API: 刷新个股详情（从网络获取最新数据）"""
            try:
                fresh_detail = get_stock_detail(code)
                if fresh_detail:
                    self.db.save_stock_detail(
                        code=code,
                        name=fresh_detail.get('name', ''),
                        latest_price=fresh_detail.get('latest_price', 0),
                        change_pct=fresh_detail.get('change_pct', 0),
                        comment=fresh_detail.get('comment'),
                        news=fresh_detail.get('news')
                    )
                    
                    detail = self.db.get_stock_detail(code)
                    return jsonify({
                        'success': True,
                        'detail': detail,
                        'message': '数据已刷新'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': '无法获取最新数据'
                    }), 500
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'刷新失败: {str(e)}'
                }), 500
        
        @self.app.route('/api/status')
        def api_status():
            """API: 获取系统状态"""
            dates = self.db.get_available_dates()
            watchlist = self.db.get_watchlist()
            
            return jsonify({
                'success': True,
                'status': 'running',
                'time': datetime.now().isoformat(),
                'review_count': len(dates),
                'latest_review': dates[0] if dates else None,
                'watchlist_count': len(watchlist)
            })
        
        @self.app.route('/comparison')
        def comparison_page():
            """多日比较页面"""
            dates = self.db.get_available_dates()
            
            return render_template('comparison.html',
                                   dates=dates,
                                   now=datetime.now())
        
        @self.app.route('/api/comparison/market')
        def api_comparison_market():
            """API: 获取多日市场数据比较"""
            start_date = request.args.get('start_date', '')
            end_date = request.args.get('end_date', '')
            dates_param = request.args.get('dates', '')
            
            dates = []
            if dates_param:
                dates = [d.strip() for d in dates_param.split(',') if d.strip()]
            elif start_date and end_date:
                all_dates = self.db.get_available_dates()
                dates = [d for d in all_dates if start_date <= d <= end_date]
            
            if not dates:
                return jsonify({
                    'success': False,
                    'message': '请选择日期范围'
                }), 400
            
            market_data = self.db.get_market_data_by_dates(dates)
            
            return jsonify({
                'success': True,
                'dates': dates,
                'market_data': market_data,
                'count': len(market_data)
            })
        
        @self.app.route('/api/comparison/surge')
        def api_comparison_surge():
            """API: 获取多日涨停股票数据比较"""
            dates_param = request.args.get('dates', '')
            
            if not dates_param:
                return jsonify({
                    'success': False,
                    'message': '请选择日期'
                }), 400
            
            dates = [d.strip() for d in dates_param.split(',') if d.strip()]
            surge_data = self.db.get_surge_stocks_by_dates(dates)
            
            daily_summary = {}
            for item in surge_data:
                date = item['date']
                if date not in daily_summary:
                    daily_summary[date] = {
                        'date': date,
                        'count': 0,
                        'stocks': []
                    }
                daily_summary[date]['count'] += 1
                daily_summary[date]['stocks'].append(item)
            
            summary_list = sorted(daily_summary.values(), key=lambda x: x['date'])
            
            return jsonify({
                'success': True,
                'dates': dates,
                'surge_data': surge_data,
                'daily_summary': summary_list,
                'total_count': len(surge_data)
            })
        
        @self.app.route('/api/comparison/heat')
        def api_comparison_heat():
            """API: 获取多日人气排名数据比较"""
            dates_param = request.args.get('dates', '')
            top_n = request.args.get('top', 10, type=int)
            
            if not dates_param:
                return jsonify({
                    'success': False,
                    'message': '请选择日期'
                }), 400
            
            dates = [d.strip() for d in dates_param.split(',') if d.strip()]
            heat_data = self.db.get_heat_ranks_by_dates(dates)
            
            date_groups = {}
            for item in heat_data:
                date = item['date']
                if date not in date_groups:
                    date_groups[date] = []
                date_groups[date].append(item)
            
            top_heat_by_date = {}
            for date, items in date_groups.items():
                sorted_items = sorted(items, key=lambda x: x['composite_score'], reverse=True)
                top_heat_by_date[date] = sorted_items[:top_n]
            
            code_appearances = {}
            for item in heat_data:
                code = item['code']
                if code not in code_appearances:
                    code_appearances[code] = {
                        'code': code,
                        'name': item['name'],
                        'appear_count': 0,
                        'dates': [],
                        'total_score': 0.0
                    }
                code_appearances[code]['appear_count'] += 1
                code_appearances[code]['dates'].append(item['date'])
                code_appearances[code]['total_score'] += item['composite_score']
            
            frequent_stocks = sorted(
                code_appearances.values(),
                key=lambda x: (x['appear_count'], x['total_score']),
                reverse=True
            )[:20]
            
            return jsonify({
                'success': True,
                'dates': dates,
                'heat_data': heat_data,
                'top_heat_by_date': top_heat_by_date,
                'frequent_stocks': frequent_stocks
            })
        
        @self.app.route('/import')
        def import_page():
            """数据导入页面"""
            dates = self.db.get_available_dates()
            unimported_files = self.db.get_unimported_files()
            
            return render_template('import.html',
                                   dates=dates,
                                   unimported_files=unimported_files,
                                   now=datetime.now())
        
        @self.app.route('/api/import/list')
        def api_import_list():
            """API: 获取未入库文件列表"""
            files = self.db.get_unimported_files()
            
            return jsonify({
                'success': True,
                'files': files,
                'count': len(files)
            })
        
        @self.app.route('/api/import/file', methods=['POST'])
        def api_import_file():
            """API: 导入单个文件"""
            data = request.get_json()
            if not data or 'file_path' not in data:
                return jsonify({
                    'success': False,
                    'message': '缺少文件路径'
                }), 400
            
            file_path = data['file_path']
            
            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'message': f'文件不存在: {file_path}'
                }), 404
            
            success = self.db.import_review_from_json(file_path)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'成功导入: {os.path.basename(file_path)}'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'导入失败: {os.path.basename(file_path)}'
                }), 500
        
        @self.app.route('/api/import/batch', methods=['POST'])
        def api_import_batch():
            """API: 批量导入文件"""
            data = request.get_json()
            if not data or 'files' not in data:
                return jsonify({
                    'success': False,
                    'message': '缺少文件列表'
                }), 400
            
            files = data['files']
            if not isinstance(files, list):
                return jsonify({
                    'success': False,
                    'message': '文件列表格式错误'
                }), 400
            
            success_count = 0
            failed_files = []
            
            for file_item in files:
                file_path = file_item.get('file_path', '')
                if not file_path or not os.path.exists(file_path):
                    failed_files.append({
                        'file': file_path,
                        'reason': '文件不存在'
                    })
                    continue
                
                success = self.db.import_review_from_json(file_path)
                if success:
                    success_count += 1
                else:
                    failed_files.append({
                        'file': file_path,
                        'reason': '导入失败'
                    })
            
            return jsonify({
                'success': True,
                'success_count': success_count,
                'failed_count': len(failed_files),
                'failed_files': failed_files,
                'message': f'成功导入 {success_count} 个文件'
            })
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, **kwargs):
        """
        运行Web服务
        
        Args:
            host: 监听地址
            port: 监听端口
            **kwargs: 其他Flask参数
        """
        logger.info(f"Web服务启动: http://{host}:{port}")
        self.app.run(host=host, port=port, **kwargs)


# 便捷函数
def create_app(debug: bool = False) -> Flask:
    """
    创建Flask应用实例
    
    Args:
        debug: 是否启用调试模式
        
    Returns:
        Flask应用实例
    """
    web_app = WebApp(debug=debug)
    return web_app.app
