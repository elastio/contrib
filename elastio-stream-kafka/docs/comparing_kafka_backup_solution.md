# Comparing Kafka Backup Solutions

Basically there are three other ways to backup and restore data
from/to Kafka:

## File System Snapshots

This was the easiest and the most reliable way to backup data and consumer
offsets from Kafka. The procedure basically shuts down one broker
after another and performs a file system snapshot which is stored on
another (cold) disk.

**Backup Procedure:**

* Repeat for each Kafka broker:
  1. Shut down the broker
  2. Take a snapshot of the Filesystem (optional)
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
  is enough to store it without replication.
* Reduced availability as every broker needs to be turned of for a
  backup
* Incremental backups are harder to achieve (e.g. due to partition
  rebalancing)
* **POTENTIAL DATA LOSS**: If the backup is performed during a
  partition rebalance (it is very likely when the backup takes a long
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

* Support for warm cluster fail-over (active-active, active-passive)
* Support for more advanced cluster topologies

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

## `elastio-stream-kafka`
`elastio-stream-kafka` is a simple but smart application that sends and stores your data to Elastio. It can be used as intended on a local machine or virtual machine, on AWS ECS with a scheduled task or with other similar services.

**Backup Procedure:**

* Checking if a topic was previously backed up.
    * if a previously backed up topic gets last stored message offset for every partition.
    * another topic that wasn't previously backed up, stores all messages from the beginning of the topic.
* Create Kafka Consumer, connecting to cluster.
* Check if topic partitions have new messages.
* Read data from Kafka topic stream to `elastio stream backup`.
* Save the information about the time interval of a point in the recovery point tags.

**Restore Procedure:**

* Create Kafka Producer, connect to cluster.
* Run `elastio stream restore` process.
* Read data from a process and write to a topic for recovery.

**Advantages:**

* Messages offsets are automatically controlled during the  backup so that duplicate or empty recovery points are not created.
* Kafka cluster does not stop working when backing up the data.
* Default Kafka consumer group is not used.
* Easily expandable for specific tasks.
* Data from backed up interval stored in one file and could be filtered by user upon restore.

**Disadvantages:**

* Don't support automated restore of all recovery points for the topic. Should be restored manually, one by one.
* No support for restoring consumer offsets.
