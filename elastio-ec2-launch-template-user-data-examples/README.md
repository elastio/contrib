# Create EC2 Launch Template to Automate Elastio Tasks

### Author: Robert Saylor - customphpdesign@gmail.com

---

### Use Cases
- Install Elastio on Ubuntu
- Automate backing up DynamoDB

---
Before you can use the user data in the advanced section when you launch a new EC2 you must first set up the EC2 with a role.

### IAM Role

From IAM click on Roles.

Click on Create role

Select AWS Service and select EC2 from the Common use cases.

Filter the policies you wish to assign to the role. Elastio comes with 6 policies. Assign only the policies required to perform your operation to your role. See [Elastio Policies](https://docs.elastio.com/src/getting-started/elastio-policies.html) for more details.

Give the role a name and click create role.

>> Note: If you use other services such as S3, DynamoDB, etc you must also attach those permissions to your IAM role.

---
### EC2 Launch Template

Create a new EC2 launch template. In the advanced section select your IAM role and copy and paste from one of the sample bash scripts in the user data section.

See (AWS Docs)[https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-launch-templates.html] for a list of CLI commands.

>> Tip: The user data is base64 encoded.

#### Describe Template

Replace '{template_id}' with your template ID and '{template_version}' with your current template version.

```
aws ec2 describe-launch-template-versions --launch-template-id {template_id} --versions {template_version}
```

---

### Create New EC2 from Launch Template

```
aws ec2 run-instances --launch-template LaunchTemplateId={template_id},Version={template_version}
```
---
### Demo using EC2 Launch template to automate running Elastio stream backup on a DynamoDB

>> In this example we created an S3 bucket and copied the 'DynamoElastio.py' from [Elastio Contrib](https://github.com/elastio/contrib/tree/master/dynamo-db-protect-and-restore-example). The EC2 instance will then terminate after the backup is complete. You could use tools to monitor the EC2 status and the filename in Elastio stream.

[Watch Video](https://asciinema.org/a/fZewQE4eikZJa2f7RtoPXLIvT)
