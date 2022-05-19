# Elastio (MSK)Kafka Stream <!--Discuse enother naming-->
# Quick start
## Create machine:
1. Create the EC2 instance(Amazon Linux 2 AMI (HVM) - Kernel 5.10, SSD Volume Type, instance type: t2.xlagre) in the same VPC with your MSK cluster.
2. After the EC2 instance was created copy the name of the security group, and save it for later. 
3. Open the Amazon VPC console at https://console.aws.amazon.com/vpc/.
4. In the navigation pane, choose Security Groups.
5. Find the security group whose use your MSK claster.
6. Choose this row by selecting the check box in the first column.
7. In the **Inbound Rules** tab, choose **Edit inbound rules**. Choose **Add rule**.
8. In the new rule, choose **All traffic** in the **Type** column. In the second field in the **Source** column, select the security group of the client machine. This is the group whose name you saved earlier in the step 2.
9. Choose **Save rules**. Now the cluster's security group can accept traffic that comes from the client machine's security group.

## Install requirements:
1. Clone the repository or download zip with the repository.
2. Before starting instaling requirements update your pip, copy and run next command:
    ```
    python3 -m pip install --upgrade pip
    ```
3. Open **elastio-msk-kafka-stream** directory in your terminal. <!--Discuse enother naming-->
4. Install dependencies with next command:
    ```
    python3 -m pip install -r requirements.txt
    ```

## Backup:
1. Open **elastio-msk-kafka-stream** directory in your terminal. <!--Discuse enother naming-->
2. To backup Kafka message you need to run elastio_stream_kafka.py script with nexts arguments **topic_name**, **brokers**, **vault**.<br/>
    Schema of arguments:

    ```
    python elastio_stream_kafka.py backup --topic_name <Name-of-your-topic> --vault <Name-of-your-vault> --brokers <broker1> <broker2> <broker3>
    ```
    Example:

    ```
    python elastio_stream_kafka.py backup --topic_name MSKTEST3 --vault defl --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
    ```

## Restore:
1. Open **elastio-msk-kafka-stream** directory in your terminal. <!--Discuse enother naming-->
2. Make sure that you have already created a topic for data recovery. The topic is not created automatically when restoring.
3. To restore Kafka message you need to run elastio_stream_kafka.py script with nexts arguments **topic_name**, **brokers**, **rp_id**.<br/>
    Schema of arguments:

    ```
    python elastio_stream_kafka.py backup --topic_name <Name-of-your-topic> --rp_id <Id-of-your-recovery-point> --brokers <broker1> <broker2> <broker3>
    ```
    Example:

    ```
    python elastio_stream_kafka.py restore --topic_name MSKTutorialTopic --rp_id rp-01g3c0cfm6mnejk5pmq4zheham --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
    ```