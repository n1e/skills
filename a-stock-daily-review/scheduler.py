#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度模块
用于service模式下自动执行每日复盘任务
"""

import logging
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from logger import logger


class ReviewScheduler:
    """
    复盘任务调度器
    用于定时执行每日复盘任务
    """
    
    def __init__(self, execute_callback: Callable = None):
        """
        初始化调度器
        
        Args:
            execute_callback: 执行回调函数，当任务触发时调用
        """
        self.scheduler = BackgroundScheduler()
        self.execute_callback = execute_callback
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """设置事件监听器"""
        
        def job_executed(event):
            logger.info(f"定时任务执行成功: {event.job_id}")
        
        def job_error(event):
            logger.error(f"定时任务执行失败: {event.job_id}, 错误: {event.exception}")
            if event.traceback:
                logger.error(event.traceback)
        
        self.scheduler.add_listener(job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(job_error, EVENT_JOB_ERROR)
    
    def add_daily_task(self, hour: int = 21, minute: int = 0, job_id: str = "daily_review"):
        """
        添加每日定时任务
        
        Args:
            hour: 执行小时（24小时制）
            minute: 执行分钟
            job_id: 任务ID
        """
        logger.info(f"添加每日定时任务: 每天 {hour:02d}:{minute:02d} 执行")
        
        # 使用Cron触发器，每天指定时间执行
        trigger = CronTrigger(hour=hour, minute=minute)
        
        self.scheduler.add_job(
            func=self._execute_task,
            trigger=trigger,
            id=job_id,
            name="每日复盘任务",
            replace_existing=True
        )
    
    def _execute_task(self):
        """执行任务（内部方法）"""
        logger.info(f"定时任务开始执行: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            if self.execute_callback:
                self.execute_callback()
            else:
                logger.warning("未设置执行回调函数，跳过任务")
        except Exception as e:
            logger.error(f"定时任务执行异常: {e}")
            raise
    
    def start(self):
        """启动调度器"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
            
            # 打印下次执行时间
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                if next_run:
                    logger.info(f"任务 [{job.id}] 下次执行时间: {next_run}")
    
    def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("定时任务调度器已停止")
    
    def run_now(self, job_id: str = "daily_review"):
        """
        立即执行指定任务（用于手动触发）
        
        Args:
            job_id: 任务ID
        """
        job = self.scheduler.get_job(job_id)
        if job:
            logger.info(f"手动触发任务: {job_id}")
            self._execute_task()
        else:
            logger.warning(f"任务不存在: {job_id}")
    
    def get_jobs(self) -> list:
        """
        获取所有任务列表
        
        Returns:
            任务信息列表
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': str(job.next_run_time) if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs


# 全局调度器实例
_scheduler_instance: Optional[ReviewScheduler] = None


def get_scheduler(execute_callback: Callable = None) -> ReviewScheduler:
    """
    获取全局调度器实例
    
    Args:
        execute_callback: 执行回调函数（仅在首次创建时有效）
        
    Returns:
        ReviewScheduler实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ReviewScheduler(execute_callback=execute_callback)
    return _scheduler_instance
