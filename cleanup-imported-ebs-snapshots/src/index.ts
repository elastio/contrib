import { EC2Client, paginateDescribeSnapshots, DeleteSnapshotCommand } from "@aws-sdk/client-ec2";
import type { Snapshot } from "@aws-sdk/client-ec2";

const TAG_TO_DELETE_BY = 'elastio:imported-to-rp';

const ec2 = new EC2Client({});

/**
 * A handler that is invoked periodically based on an AWS Sheduler shedule
 * and cleans up EBS snapshots that were already imported to Elastio.
 */
export async function handler() {
    const paginator = paginateDescribeSnapshots(
        {
            client: ec2,
            pageSize: 1000,
        },
        {
            OwnerIds: ['self'],
            Filters: [{ Name: 'tag-key', Values: [TAG_TO_DELETE_BY] }]
        }
    );

    for await (const page of paginator) {
        const snapshots = (page.Snapshots ?? []);

        console.log(`Discovered ${snapshots.length} snapshots to cleanup`);

        await Promise.all(snapshots.map(deleteSnapshot));

        console.log(`Done processing ${snapshots.length} snapshots`);
    }
}

async function deleteSnapshot(snapshot: Snapshot) {
    const snapshotId = snapshot.SnapshotId;

    if (snapshotId == null) {
        console.error("Found a snapshot without a SnapshotId. Skipping it.", snapshot);
        return;
    }

    const tag = snapshot.Tags?.find(tag => tag.Key === TAG_TO_DELETE_BY);

    if (tag == null) {
        // It should be a bug if we get here.
        // We must filter by this tag in the DescribeSnapshots query.
        console.error(
            `Found a snapshot without the tag '${TAG_TO_DELETE_BY}'. Skipping it.`,
            snapshot
        );
        return;
    }

    console.log(`Deleting the EBS snapshot (${TAG_TO_DELETE_BY}=${tag.Value}) ${snapshotId}`);

    await ec2.send(new DeleteSnapshotCommand({ SnapshotId: snapshotId }));
}
