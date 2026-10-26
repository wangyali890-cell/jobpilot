"""公开演示专用的虚构岗位。"""

from datetime import timedelta

from jobpilot.domain.service import JobService


def seed_demo(service: JobService) -> None:
    today = service.today_provider()
    service.create_job(
        {
            "company": "星河科技（演示）",
            "job_title": "产品经理实习生",
            "city": "上海",
            "job_type": "实习",
            "deadline": today + timedelta(days=3),
            "next_action": "完善作品集并投递",
            "next_action_date": today + timedelta(days=1),
            "notes": "虚构演示记录，请勿填写真实个人信息。",
        }
    )
    service.create_job(
        {
            "company": "远山数字（演示）",
            "job_title": "增长产品经理",
            "city": "北京",
            "status": "已投递",
            "deadline": today + timedelta(days=7),
            "next_action": "查看投递邮件",
            "next_action_date": today + timedelta(days=2),
        }
    )
    service.create_job(
        {
            "company": "云帆研究（演示）",
            "job_title": "用户研究实习生",
            "city": "深圳",
            "status": "面试",
            "deadline": today - timedelta(days=1),
            "next_action": "准备面试问题",
            "next_action_date": today + timedelta(days=4),
        }
    )
    service.create_job(
        {
            "company": "松石实验室（演示）",
            "job_title": "产品运营",
            "city": "杭州",
            "status": "已结束",
            "deadline": today - timedelta(days=2),
        }
    )
