from sqladmin import ModelView
from apps.ever_apply.models import User, Job, JobMatch


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.clerk_user_id, User.email, User.resume_url, User.is_free, User.created_at]
    column_editable_list = [User.is_free]
    column_searchable_list = [User.email, User.clerk_user_id]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"


class JobAdmin(ModelView, model=Job):
    column_list = [Job.id, Job.title, Job.company, Job.location, Job.remote_type, Job.source, Job.expires_at, Job.created_at]
    column_searchable_list = [Job.title, Job.company]
    name = "Job"
    name_plural = "Jobs"
    icon = "fa-solid fa-briefcase"


class JobMatchAdmin(ModelView, model=JobMatch):
    column_list = [JobMatch.id, JobMatch.user_id, JobMatch.job_id, JobMatch.score, JobMatch.status, JobMatch.created_at]
    name = "Job Match"
    name_plural = "Job Matches"
    icon = "fa-solid fa-star"
