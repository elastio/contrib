// @ts-check

const { EC2, paginateDescribeVolumes } = require('@aws-sdk/client-ec2');
const ec2 = new EC2();

const isVolumeOlderThan24Hours = (createTime) => {
    const currentTime = new Date();
    const volumeCreateTime = new Date(createTime);
    const timeDifference = currentTime - volumeCreateTime;
    const hoursDifference = timeDifference / (1000 * 60 * 60);
    return hoursDifference > 24;
};

exports.handler = async (_event) => {
    try {
        console.log("Getting list of unattached EBS volumes with elastio:resource tag");

        const volumesPaginator = paginateDescribeVolumes(
            {
                client: ec2,
                pageSize: 500.
            },
            {
                Filters: [
                    {
                        Name: 'status',
                        Values: ['available']
                    },
                    {
                        Name: 'tag:elastio:resource',
                        Values: ['*']
                    }
                ]
            }
        );

        for await (const page of volumesPaginator) {
            for (const volume of page.Volumes ?? []) {
                if (isVolumeOlderThan24Hours(volume.CreateTime)) {
                    console.log(`Deleting unattached Elastio EBS volume ${volume.VolumeId} older than 24 hours`);
                    await ec2.deleteVolume({ VolumeId: volume.VolumeId });
                    console.log(`EBS volume ${volume.VolumeId} deleted`);
                } else {
                    console.log(`EBS volume ${volume.VolumeId} is not old enough; skipping it`);
                }
            }
        }

        return { statusCode: 200, body: JSON.stringify({ message: 'EBS volumes cleanup successful' }) };
    } catch (error) {
        console.error(error);
        throw error;
    }
};
