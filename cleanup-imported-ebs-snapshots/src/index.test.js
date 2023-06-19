//@ts-check
const { expect, test } = require('@jest/globals');
const { CleanupContext } = require('../dist/index');
const { it } = require('node:test');

// Pretend today is the 10th day since the epoch
const NOW = 10;

/** @param {number[]} daysFromNow */
function deletedSnapshots(daysFromNow) {
  const options = {
    now: new Date(NOW * 1000 * 60 * 60 * 24),
    // Pick lower values for easier testing
    keepMinAmount: 2,
    keepMaxAgeInDays: 4,
  };

  const snapshots = daysFromNow.map(startDay => ({
    snapshotId: 'snap-1234567890abcdef0',
    startTime: new Date(startDay * 1000 * 60 * 60 * 24),
    tagValue: "baz",
  }));

  const volume = "vol-abc123";
  const snapshotsMap = new Map([[volume, snapshots]]);
  const cleanup = new CleanupContext(options, snapshotsMap);

  cleanup.filterSnapshotsToDelete();

  return cleanup.snapshots.get(volume)?.map(snap => snap.startTime.getTime() / (1000 * 60 * 60 * 24));
}

test('filterSnapshotsToDelete', () => {
  it('smoke', () => {
    const snaps = [1, 4, 5, 3, 2];

    // We must keep the last 2 snapshots (4 and 5)
    expect(deletedSnapshots(snaps)).toStrictEqual([1, 2, 3]);
  });

  it("doesn't keep the list in the volumes map if no snapshots are to be removed", () => {
    expect(deletedSnapshots([])).toBeUndefined();
    expect(deletedSnapshots([2])).toBeUndefined();
    expect(deletedSnapshots([1, 2])).toBeUndefined();
  });

  it('retains at least the given threshold of snapshots even if they are all old', () => {
    const snaps = [3, 2, 1];
    expect(deletedSnapshots(snaps)).toStrictEqual([1]);
  });

  it('retains all if they are within the max days threshold', () => {
    const snaps = [8, 8, 9, 9, 10, 10, 10, 7];
    expect(deletedSnapshots(snaps)).toBeUndefined();

    snaps.push(5);
    expect(deletedSnapshots(snaps)).toStrictEqual([5]);
  });
});
