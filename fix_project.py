import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from videos.models import VideoProject

def fix_stale_project():
    try:
        # The ID from the logs/user request
        project = VideoProject.objects.get(id='b2cdda19-4dbb-4de0-98cf-642252df55cc')
        if project.status == VideoProject.Status.PROCESSING:
            print(f"Updating project {project.id}...")
            # We know it's completed from the debug script
            project.status = VideoProject.Status.COMPLETED
            # URL from debug script (I'll just put a placeholder or fetch it again if I could parse the output, 
            # but I'll simpler just trigger the monitor task ONE LAST TIME to auto-fix it)
            
            from videos.tasks import monitor_video_status_task
            monitor_video_status_task.delay(project.id)
            print("Triggered monitor task to update status.")
    except VideoProject.DoesNotExist:
        print("Project not found.")

if __name__ == "__main__":
    fix_stale_project()
