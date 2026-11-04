from celery import shared_task
@shared_task
def send_notification(recipient_email, subject, message):
    # Replace with provider-backed email; intentionally logs payload in MVP.
    print(f"Notification to={recipient_email} subject={subject}: {message}")
@shared_task
def build_workspace_report(workspace_id):
    from .models import Issue
    qs=Issue.objects.filter(workspace_id=workspace_id)
    return {"workspace_id":workspace_id,"total":qs.count(),"done":qs.filter(status="done").count()}
