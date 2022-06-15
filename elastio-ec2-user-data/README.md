# Install Elastio via AWS EC2 User Data

### Author: Robert Saylor - customphpdesign@gmail.com

---

Before you can use the user data in the advanced section when you launch a new EC2 you must first set up the EC2 with a role.

### IAM Role

From IAM click on Roles.

Click on Create role

Select AWS Service and select EC2 from the Common use cases.

Filter the policies you wish to assign to the role. Elastio comes with 6 policies. Assign all the Elastio policies to your role. See [Elastio Policies](https://docs.elastio.com/src/getting-started/elastio-policies.html) for more details.

Give the role a name and click create role.

### EC2

Launch a new EC2 or create a launch template.

Under advanced details:

IAM instance profile:

select your role you created earlier.

User data:

Copy and paste from the example provided in this folder for the OS you are installing.

Then click Launch instance

### Running Elastio

Once your EC2 starts both AWS CLI and Elastio CLI will be available to the instance.

