from django.test import TestCase
from rest_framework.test import APIClient
from .models import User,Workspace,Membership,Project,Issue
class TenantBoundaryTests(TestCase):
 def setUp(self):
  self.a=User.objects.create_user(username="a@x.test",email="a@x.test",password="StrongPassword123")
  self.b=User.objects.create_user(username="b@x.test",email="b@x.test",password="StrongPassword123")
  self.wa=Workspace.objects.create(name="A",slug="a"); self.wb=Workspace.objects.create(name="B",slug="b")
  Membership.objects.create(workspace=self.wa,user=self.a,role="owner"); Membership.objects.create(workspace=self.wb,user=self.b,role="owner")
  self.pa=Project.objects.create(workspace=self.wa,name="Private",key="PRV")
  Issue.objects.create(workspace=self.wa,project=self.pa,title="Secret",reporter=self.a,issue_no=1)
 def token(self,email,password):
  c=APIClient(); r=c.post("/api/auth/token/",{"email":email,"password":password},format="json"); return r.data["access"]
 def test_other_workspace_issues_not_visible(self):
  c=APIClient(); c.credentials(HTTP_AUTHORIZATION="Bearer "+self.token("b@x.test","StrongPassword123"))
  r=c.get("/api/issues/"); self.assertEqual(r.status_code,200); self.assertEqual(r.data,[])
 def test_project_create_workspace_scoped(self):
  c=APIClient(); c.credentials(HTTP_AUTHORIZATION="Bearer "+self.token("b@x.test","StrongPassword123"))
  r=c.post("/api/sprints/",{"project":self.pa.id,"name":"Intrude"},format="json")
  self.assertIn(r.status_code,[400,403])
 def test_health(self):
  self.assertEqual(APIClient().get("/api/health/").status_code,200)
