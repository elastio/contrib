# Kafka Stream Backup with Elastio <!--Discuss another naming-->

# The need for a Backup Solution for Kafka
Kafka is a highly distributed system and can be configured to provide
a high level of resilience on its own. Using a large replication
factor we can survive the loss of several brokers and when we stretch
out Kafka Cluster across multiple data centers (the latency should stay
below 30ms), we can even survive the loss of data centers! So why should
we care about backups if we can just increase the distribution of
Kafka?

## Replication does not replace backups
Replication handles many error cases, but by far not all. What if there is 
a bug in Kafka that deletes old data? What about a misconfiguration of the 
topic (are you sure that your values of replica.lag.max.messages, 
replica.lag.time.max.ms are good values?). What if an admin has accidentally 
deleted the Prod Cluster because he thought he was on dev? 
What about security breaches? If an attacker gets access to your Kafka 
Management interface, they can do whatever they like.

If you use Kafka as your "main system" for your company and you store your
core business data in Kafka, you'd better think about a cold storage backup
for your Kafka Cluster.

## Why should I pay for the additional Kafka Clusters?
In case with Kafka replication solves more complex problems, but actually you
pay for storing your copied data in the neighboring topic or in another cluster.
If you do not use Kafka for "Big Data" applications, you are probably totally fine
with just one small Kafka Cluster. Maybe your applications run only in one data
center and this is totally ok for you. Then there is probably no need to set up
and operate additional Kafka Clusters. If your data center with all your
applications shuts down, what's the use to stretch high available Kafka Cluster?
You would be probably absolutely fine if you have just a backup  of all your data 
on an storage that you could replay to restore operations.

# What is Kafka Stream Backup with Elastio?
Kafka Stream backup with Elastio consists of two pieces: one for `Backup(implemented as python-kafka
Consumer with elastio stream backup)` and one for the `Restore(implemented as python-kafka
Producer with elastio stream restore)`.

The `Backup` from the python-kafka consumer connects to a Kafka Broker and continuously
fetches data from the specified topic and writes it to Elastio vault. Similarly to Kafka,
Elastio Stream backup does not change the data, but writes it without modification
as bytes to Elastio vault. Kafka Stream Backup with Elastio uses incremental backup of data
to minimize storage space and excludes duplication of data.

Similarly, the `Restore` connects to Kafka Brokers and streams data in the Elastio vault.
To reduce errors, you need to explicitly define the topic to restore. 
Kafka Stream backup with Elastio does not restore `__consumer_offsets`.It is not enough to 
just copy the__consumer_offsets topic because the actual offsets of the messages may be changed.
In order to keep the correct sequence of records and their position,
we segregate them by partition in for each topic.


# Use cases
1. Backup and Restore Kafka topic in original formats.
2. Backup and Restore Kafka internal topics: `__consumer_offsets`, 
`__amazon_msk_canary`. Don't try backup topics: `_schemas`, because is
used by Schema Registry to store all the schemas,
metadata and compatibility configuration this topic
couldn't be changed/write by user.


# Setup
[Quick Start Guide](docs/quick_start.md)
1. Clone the repository or download .zip file with the repository.
2. Before installing update your `pip`, copy and run the following command:
   
    ```
    python3 -m pip install --upgrade pip
   
    ```
3. Open **elastio-stream-kafka** directory in your terminal. <!--Discuss another naming-->
4. Install dependencies with the following command:
   
    ```
    python3 -m pip install -r requirements.txt
    ```


# Alternatives
## File System Snapshots

This was the easiest and the most reliable way to backup data and consumer
offsets from Kafka. The procedure basically shuts down one broker
after another and performs a file system snapshot which is stored on
another (cold) disk.

**Backup Procedure:**

* Repeat for each Kafka broker:
  1. Shut down the broker
  2. Take a snapshot of the filesystem (optional)
  3. Copy the snapshot (or simply the files) to the backup storage
  4. Turn on the broker and wait until all partitions are in sync mode

**Restore Procedure:**

* Restore the snapshot for each broker
* Boot the brokers

**Advantages:**

* Uses native OS tools
* As this procedure needs to be done very often, the fear of shutting
  down a broker is minimized (especially for a team and environment
  with little Kafka expertise)
* Offsets are backed up and restored correctly
* Internal topics are backed up and restored correctly
* Compacted messages are deleted too
* Messages that exceeded the retention period are deleted as well
* Uses cold storage

**Disadvantages:**

* Each message is backed up by a `replication factor`number of times. Even if it
  is sufficient to store it without replication.
* Reduced availability as every broker needs to be turned off for a
  backup
* Incremental backups are harder to achieve (e.g. due to partition
  rebalancing)
* **POTENTIAL DATA LOSS**: If the backup is performed during a
  partition rebalancing (it is very likely when the backup takes a long
  time), the backup could miss a whole partition due to bad timing.

## Using Mirror Maker 2 to backup data to another Cluster

The traditional Mirror Maker has many issues as discussed in
[KIP-382](https://cwiki.apache.org/confluence/display/KAFKA/KIP-382%3A+MirrorMaker+2.0).
Kafka Mirror Maker 2 solves many of these and can be used to back up data from one cluster to another.

**Backup Procedure A+B (normal setup):**

* Set up the MM2 Connector that copies the data from the topic
  `[topic]` on the source cluster to the topic
  `[source-cluster-name].[topic]` on the cluster name.
* Mirror Maker 2 ensures that the messages are being copied continuously.
  Offsets are also copied to a separate topic.

**Backup Procedure C (for consistent Snapshots):**

* Set up the sink (backup) cluster with one broker.
* Set up the topics on the sink cluster with a replication factor of
  `1`.
* Set up MM2 to copy data from the source cluster to the sink cluster.
* Use a cronjob to shut down the sink cluster (with one broker)
  regularly and take a snapshot of the file system and store them on
  cold storage.

**Restore Procedure A (Use other cluster):**

* Use the offset sync topic to configure the consumer groups to
  consume from the correct offset.
* Setup the consumers to use the other cluster. Discard the old
  one.
* Set up the clients to produce and consume from the new topics in the
  new cluster.
* Set up a new Backup Cluster.

**Restore Procedure B (Mirror data back):**

* Create a new Kafka Cluster.
* Set up Mirror Maker 2 to copy the data to the new cluster.
* Continue with procedure A.

**Restore Procedure C (Mirror + Snapshot):**

* Use Procedure B or restore a new cluster from the file system
  snapshots.
* Add more nodes respectively.
* Increase the replication factor to match the requirements.
* Rebalance the partitions if needed.
* Continue with procedure A.

**Advantages:**

* Supports for warm cluster fail-over (active-active, active-passive)
* Supports for more advanced cluster topologies

**Disadvantages:**

* Requires a second Kafka Cluster
* Apart from `C` this is a warm backup and does not protect from
  bugs in Kafka or the underlying OS
* Requires custom implementation of the switch-over handling to the
  restored cluster
* Adds a lot of complexity in the setup

## `kafka-connect-s3`

`kafka-connect-s3` is a popular Kafka Connect connector to mirror the
data from topics to Amazon S3 (or compatible other services like
Minio). Zalando describes a setup in their article [Surviving Data
Loss](https://jobs.zalando.com/tech/blog/backing-up-kafka-zookeeper/)

**Backup procedure:**

* Set up the sink connector to use your S3 endpoint.
* Set up another sink connector that backs up the `__consumer_offsets` topic.

**Restore procedure:**

* Set up the source connector to read the data from S3 into Kafka.
* Manually extract the new offset for the consumers and manually
  identify which offset on the new Kafka cluster matches the old
  one. (This is not a trivial task – you would need to count the ACK'd
  messages from the beginning to find out the exact offset – and do not
  forget about compacted and deleted messages).

**Advantages:**

* Cold backup (to S3).
* Possible to use in downstream services that work only with S3 (e.g. Data
  Warehouses).

**Disadvantages:**

* Supports only S3 (and compatible systems) as the storage backend.
* No support for restoring consumer offsets (the method described above could be described as solution for one case and will not work in many cases)