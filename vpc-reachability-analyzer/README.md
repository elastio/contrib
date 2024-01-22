# Verify Subnet Configuration for Elastio

This folder contains a Bash script which can be used to automatically check the subnet(s) in an Amazon VPC, to determine
if they have the necessary network access to be used with Elastio.

You may run this script on any Linux or macOS system, but the most convenient way for most customers is to run it inside
of an AWS CloudShell instance, in the region where you plan to deploy Elastio.

To run the script, open a terminal (if using AWS CloudShell, open CloudShell by clicking on the CloudShell icon at the
top of the AWS Console, to the left of the bell icon) and run the following commands:

```
wget -q -O elastio-vpc-test.sh https://raw.githubusercontent.com/elastio/contrib/master/vpc-reachability-analyzer/elastio-vpc-test.sh
chmod +x elastio-vpc-test.sh
./elastio-vpc-test.sh
```

> NOTE: if you have an SCP or other policy mechanism that requires EC2 instances be created with certain tags, 
> use the `--instance-tags` argument to the `elastio-vpc-test.sh` script to specify the tags.  Here's an example of how
> you can modify the last line in the script above to set tags:
> 
> ```
> ./elastio-vpc-test.sh --instance-tags Key=my-custom-tag,Value=foo,Key=my-other-custom-tag,Value=bar
> ```

The script will output some instructions, and then a list of VPCs available to test, for example:

```
This script automates the process of evaluating the subnets within a VPC to test if they have the necessary access to be used with Elastio.

To use it, choose the VPC you want to evaluate from the list, and the script will test each subnet in that VPC, one by one, by performing a Network Reachability Analyzer analysis.

NOTE: This script will launch one very short-lived t2.micro instance in each subnet of the VPC, and it will perform Network Reachability Analyzer analysis, both of which incurr AWS charges. These
charges are very small, but they will be incurred.

Please also note that this script only works within the AWS environment and requires appropriate permissions to create and manage EC2 instances and network paths. Ensure you have these permissions
before running the script to avoid execution errors.

Discovering available VPCs in us-east-2...

1: vpc-e2563889 (Name: None, IsDefault: True)
2: vpc-01a77fdcee459e9e6 (Name: ElastioTest, IsDefault: False)

Select VPC (Press Enter to select VPC 1, or Ctrl-D to abort): 
```

To proceed further, enter the number of the VPC to analyze.  The script will run for a few minutes, outputting updates
as to its progress.  At the end it will print a list of all subnets in the VPC, and whether or not the Internet is
reachable from each one.  The output looks like this:


```
Subnet Analysis Results:
(Subnets with a value of 'True' for Internet reachability can be used with Elastio)
  subnet-935f68df - Auto-assign public IPv4: True; Internet reachable: True
  subnet-4d48de26 - Auto-assign public IPv4: True; Internet reachable: True
  subnet-4744883a - Auto-assign public IPv4: True; Internet reachable: True
```

If a subnet can be used with Elastio, it is listed as "Internet reachable: True".  If it's not suitable for use with
Elastio, the value will be `False`.

If a subnet reports `False` for internet reachability, review the corresponding Network Insights path created 
by the script, to understand why exactly it produced that result.

For more information on how to configure a VPC for use by Elastio, see the [Elastio docs on VPC
configuration](https://docs.elastio.com/docs/get-started/deployment-specifications/vpc-config).
