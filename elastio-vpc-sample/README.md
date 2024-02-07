# Elastio Sample VPC

This Cloudformation template provides a reference VPC example, which has been properly configured for use with Elastio.

Elastio does not require a dedicated VPC, and is designed to be able to use the VPCs, subnets, and other network resources that customers already have in their infrastructure.  However it does require that each subnet into which Elastio is deployed be able to access the Internet, either directly via an Internet gateway, indirectly via a NAT gateway, or via some customer-specific network topology that routes through a transit gateway, on-prem network, third-party firewall, or some other means.  No matter what the network topology, Elastio worker instances must be able to reach the specific URLs that are required for Elastio to function, which include (but are not limited to):

- All AWS API endpoints (which all have DNS names ending in `amazonaws.com`)
- The ECR Public container registry at `public.ecr.aws`
- CDN endpoints used by Elastio iScan for malware and ransomware definitions.

For a current list of all URLs Elastio must access, see the [troubleshooting section of the Elastio docs](https://docs.elastio.com/docs/reference/troubleshooting#adding-urls-accessed-by-elastio-to-the-whitelist).

The above notwithstanding, many customers are unsure how exactly a VPC must be configured for compatibility with Elastio and adherence to best practices.  This Cloudformation template provides a quick and easy way to deploy a VPC that is pre-qualified by Elastio for compatibility.  Customers can then modify this VPC to fit their policies, or adjust the Cloudformation template itself as needed.

For help determining if an existing VPC is suitable for use with Elastio, or if it's not working to determine why not, see also the [Elastio VPC reachability script](../vpc-reachability-analyzer/).

## What This Sample Does

This Cloudformation template will create a new VPC, with three private subnets spread across three availability zones, and one public subnet.  Each private subnet will have access to the Internet via a single, shared NAT gateway located in the single public subnet.  An Internet gateway is also deployed in the public subnet to provide a route to the Internet for the NAT gateway.  Each of the subnets has a `/20` CIDR, providing approximately 4000 usable IP addresses per subnet.  This is more than enough for Elastio's needs (although a `/24` with 254 usable IP addresses might not be enough for large customers running hundreds of jobs in parallel, which is why by default we use a `/20`).

## How Much Will This Sample Cost

Most of the resources deployed in this sample are free.  One important exception is that NAT gateway.  Always refer to the [official AWS VPC Pricing](https://aws.amazon.com/vpc/pricing/) for the latest information, but as of this writing in the US regions, a single NAT gateway costs $0.045/hr, plus $0.045/GB of traffic.  This comes out to $32.40/mo plus whatever the traffic cost is.

Due to the way Elastio works, the majority of traffic Elastio generates is to or from S3.  Since this template deploys an S3 gateway VPC endpoint, all S3 traffic will bypass the NAT gateway and go directly to S3, so in most cases the volume of traffic over the NAT gateway will be low, but it's not possible to predict how much it will be and thus how much it will cost.  In all but the most extreme cases, the cost of the NAT gateway including Elastio-generated traffic should be well under $100/mo.

Another variable cost to this VPC is the cross-AZ traffic.  Precisely because the NAT gateways are not free, we have chosen to deploy a single NAT gateway in a single availability zone, with the two other private subnets routing their Internet traffic across AZ boundaries to the AZ housing the NAT gateway.  As of this writing, the [AWS in-region data transfer pricing](https://aws.amazon.com/ec2/pricing/on-demand/#Data_Transfer_within_the_same_AWS_Region) for cross-AZ traffic is $0.02/GB ($0.01 for traffic leaving one AZ and $0.01 for that same traffic entering the destination AZ).  This means that traffic to the Internet originating in the second or third subnet will incur cross-AZ bandwidth charges as well as NAT gateway bandwidth charges.  S3 traffic is exempt from this due to the use of S3 gateway VPC endpoints.  This is unlikely to be a significant amount of traffic under normal Elastio usage scenarios, but we call it out here nonetheless in the interest of completeness.

## How to Deploy This Sample

To deploy this sample, you must first download the Cloudformation template locally.  To do that, right-click this [download Cloudformation template](https://github.com/elastio/contrib/blob/master/elastio-vpc-sample/elastio-sample-vpc-template.yaml) link, and choose "Save Link As" or whatever your browser's equivalent is, choosing to save this file in some directory (often the `Downloads`) directory.  Make a note of where you saved it, as that will be important later.

Next, log in to the AWS console in the account where you want to create the VPC.  Go to the Cloudformation console, and make sure you are in the region where you want the VPC deployed.

From the Cloudformation console, click **Create Stack**.  The default option **Template is ready** should be selected.  For _Template Source_, choose the option **Upload a template file**, then click the _Choose File_ button and browse to the `elastio-sample-vpc-template.yaml` file you downloaded earlier, and then click **Next**.

Choose a stack name for this Cloudformation stack.  Any name will work; for example `elastio-vpc`.

Next review the **Parameters** section to see the options that you can specify to the Cloudformation template to control the resulting VPC.  If your company has naming conventions that require certain prefixes or suffixes, you can enter those separately for VPC and subnet-level resources in the parameters `VpcPrefix/VpcSuffix` and `SubnetPrefix/SubnetSuffix`, respectively.  You're also able to control the private network CIDR block used by the VPC, although unless you have a specific reason to change these and know what you are doing we recommend you accept the defaults.

When you are satisfied with the Parameters, click **Next**

On the next screen you can add any tags that you like, particularly if your organization has rules requiring particular tags on stacks or the resources they create.

Otherwise, scroll down past the other stack options, leaving everything set to default, and click **Next**.

On the last screen, accept all defaults, scroll all the way down, and click **Submit**.

The stack will take a minute or two to deploy, at which point you should have a new VPC, subnets, and other resources that you can use with Elastio.
