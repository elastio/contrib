import { EC2Client, paginateDescribeSnapshots, DeleteSnapshotCommand } from "@aws-sdk/client-ec2";

// This volume ID can appear in real EBS snapshots when the snapshot was
// copied from an other snapshot. We will skip such snapshots, because
// we don't know what the original volume ID was, and can't decide if
// there will be enough snapshots for that volume if we delete some of them.
const BROKEN_VOLUME_ID = 'vol-ffffffff';

const ec2 = new EC2Client({});

/**
 * A handler that is invoked periodically based on an AWS Scheduler schedule
 * and cleans up EBS snapshots that were already imported to Elastio.
 */
export async function handler() {
    const now = new Date();

    console.log(`Starting the cleanup relative to the current timestamp ${now.toISOString()}`);

    const options = {
        deleteByTagKey: getEnv('DELETE_BY_TAG_KEY'),
        keepMinAmount: Number(getEnv('KEEP_MIN_AMOUNT')),
        keepMaxAgeInDays: Number(getEnv('KEEP_MAX_AGE_IN_DAYS')),
    }

    const cleanup = await CleanupContext.discoverSnapshots({ now, ...options });

    const considered = cleanup.total();

    if (considered.snapshots === 0) {
        console.log(`Nothing to do. Exiting.`);
        return;
    }

    console.log(`Discovered ${considered.toString()} considered for cleanup`);

    cleanup.filterSnapshotsToDelete();

    const filtered = cleanup.total();

    console.log(`Planning to delete ${filtered.toString()}`);

    await cleanup.deleteSnapshots();

    console.log(`Done processing ${filtered.toString()}`);
}

function getEnv(name: string): string {
    const value = process.env[name];
    if (value == null) {
        throw new Error(`DELETE_BY_TAG_KEY is not set`);
    }
    return value;
}

interface SnapshotWithTag {
    snapshotId: string,
    startTime: Date,
    tagValue: string,
}

interface CleanupOptions {
    now: Date,
    deleteByTagKey: string,
    keepMinAmount: number,
    keepMaxAgeInDays: number
}

class CleanupTotal {
    constructor(public volumes: number, public snapshots: number) { }

    toString() {
        return `${this.snapshots} snapshots for ${this.volumes} volumes`;
    }
}

export class CleanupContext {
    constructor(
        private options: CleanupOptions,
        private snapshots: Map<string, SnapshotWithTag[]>,
    ) { }

    static async discoverSnapshots(options: CleanupOptions): Promise<CleanupContext> {
        const paginator = paginateDescribeSnapshots(
            {
                client: ec2,
                pageSize: 1000,
            },
            {
                OwnerIds: ['self'],
                Filters: [{ Name: 'tag-key', Values: [options.deleteByTagKey] }]
            }
        );

        let snapshots = new Map<string, SnapshotWithTag[]>();

        for await (const page of paginator) {
            for (const snapshot of page.Snapshots ?? []) {
                if (
                    snapshot.SnapshotId == null ||
                    snapshot.StartTime == null ||
                    snapshot.VolumeId == null ||
                    snapshot.State == null
                ) {
                    console.error(
                        `Skipping a snapshot without some of the required fields`,
                        snapshot
                    );
                    continue;
                }

                if (snapshot.VolumeId == BROKEN_VOLUME_ID) {
                    console.error(
                        `Skipping a snapshot with the broken volume ID (${snapshot.VolumeId}). ` +
                        `It's possible this snapshot was copied from an other snapshot. ` +
                        `We don't support such snapshots.`,
                        snapshot
                    );
                    continue;
                }

                const tag = snapshot.Tags?.find(tag => tag.Key === options.deleteByTagKey);

                if (tag == null) {
                    // It should be a bug if we get here.
                    // We must filter by this tag in the DescribeSnapshots query.
                    console.error(
                        `Found a snapshot without the tag '${options.deleteByTagKey}'. Skipping it.`,
                        snapshot
                    );
                    continue;
                }

                if (tag.Value == null) {
                    console.error(
                        `Found a snapshot with the tag '${options.deleteByTagKey}' ` +
                        `but without the value. Skipping it.`,
                        snapshot
                    );
                    continue;
                }

                if (snapshot.State !== 'completed') {
                    console.error(
                        `Found a snapshot with the tag '${options.deleteByTagKey}' ` +
                        `but with the state '${snapshot.State}'. Skipping it.`,
                        snapshot
                    );
                    continue;
                }

                const newSnapshot: SnapshotWithTag = {
                    snapshotId: snapshot.SnapshotId,
                    startTime: snapshot.StartTime,
                    tagValue: tag.Value,
                };

                const volumeSnapshots = snapshots.get(snapshot.VolumeId);
                if (volumeSnapshots == null) {
                    snapshots.set(snapshot.VolumeId, [newSnapshot]);
                    continue;
                }

                volumeSnapshots.push(newSnapshot);
            }
        }

        return new CleanupContext(options, snapshots);
    }

    total(): CleanupTotal {
        const volumes = this.snapshots.size;
        const snapshots = [...this.snapshots.values()]
            .reduce((acc, snapshots) => acc + snapshots.length, 0);
        return new CleanupTotal(volumes, snapshots);
    }

    /**
     * Retain only snapshots that need to be deleted
     */
    filterSnapshotsToDelete() {
        const toDeleteMap = new Map<string, SnapshotWithTag[]>();

        for (const [volumeId, toDelete] of this.snapshots) {
            if (toDelete.length <= this.options.keepMinAmount) {
                // We don't have enough snapshots to delete any of them.
                continue;
            }

            // Sort in ascending order by the start time (oldest snapshots first)
            toDelete.sort((a, b) => a.startTime.getTime() - b.startTime.getTime());

            // Find the first snapshot that is within `KEEP_SNAPSHOTS` time threshold
            const firstKeptByTime = toDelete.findIndex(snapshot => {
                const snapshotAge = this.options.now.getTime() - snapshot.startTime.getTime();
                const snapshotAgeInDays = snapshotAge / (1000 * 60 * 60 * 24);

                return snapshotAgeInDays <= this.options.keepMaxAgeInDays;
            });

            let firstKept = toDelete.length - this.options.keepMinAmount;
            if (firstKeptByTime >= 0 && firstKeptByTime < firstKept) {
                firstKept = firstKeptByTime;
            }

            if (firstKept === 0) {
                continue;
            }

            toDeleteMap.set(volumeId, toDelete.slice(0, firstKept));
        }

        this.snapshots = toDeleteMap;
    }

    async deleteSnapshots() {
        for (const [volumeId, snapshotsToDelete] of this.snapshots) {
            const promises = snapshotsToDelete.map(async snapshot => {
                const { snapshotId, tagValue, startTime } = snapshot;
                console.log(
                    `Deleting the EBS snapshot ` +
                    `(${this.options.deleteByTagKey}=${tagValue}) ${snapshotId} ` +
                    `created at ${startTime.toISOString()} for the volume ${volumeId}`
                );
                await ec2.send(new DeleteSnapshotCommand({ SnapshotId: snapshotId }));
            });

            await Promise.all(promises);

            console.log(
                `Deleted ${snapshotsToDelete.length} snapshots for the volume ${volumeId}`
            );
        }
    }
}
