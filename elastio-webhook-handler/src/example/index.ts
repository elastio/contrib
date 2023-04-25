/**
 * This module shows example of business logic triggered by events processing itself.
 */

class RecoveryPointsRepository {
    static scannedRecoveryPoints = new Map<string, CyberScannedRecoveryPoint>()
}

interface CyberScannedRecoveryPoint {
    id: string;
    elastioAssetId: string;
    malwareDetected: boolean;
    ransomwareDetected: boolean;
    lastScanTime: Date;
}

interface EventAttributes {
    id: string;
    kind: string;
    eventTime: Date;
    labels: any; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export class Event {
    private readonly attributes: EventAttributes;

    constructor(attributes: EventAttributes) {
      this.attributes = attributes;
    }

    get id(): string {
      return this.attributes.id;
    }

    get kind(): string {
        return this.attributes.kind;
    }

    get eventTime(): Date {
        return this.attributes.eventTime;
    }

    getLabel(name: string): any { // eslint-disable-line @typescript-eslint/no-explicit-any
        return this.attributes.labels[name]; // eslint-disable-line security/detect-object-injection
    }
}

export function processEvent(elastioEvent: any): void { // eslint-disable-line @typescript-eslint/no-explicit-any
    const { event_id, event_kind, event_time, ...labels } = elastioEvent;

    const eventTimestamp = Date.parse(event_time);
    if (isNaN(eventTimestamp)) {
        throw new Error(`Event "${event_id}" has invalid timestamp "${event_time}"`);
    }

    const event = new Event({
        id: event_id,
        kind: event_kind,
        eventTime: new Date(eventTimestamp),
        labels,
    });

    applyEvent(event);
}

// Events labels may vary and will be updated individually,
// so we advise you to process each event kind separately.

function applyEvent(event: Event): void {
    console.info(`Processing event "${event.id}" of kind ${event.kind}`);

    switch (event.kind) {
        case "elastio:recovery-point:iscan:healthy":
            applyRecoveryPointHealthyEvent(event);
            console.info("Healthy recovery point detected");
            break;
        case "elastio:recovery-point:iscan:unhealthy":
            applyRecoveryPointUnhealthyEvent(event);
            console.warn("Unhealthy recovery point detected");
            break;
        default:
            console.warn(`Unsupported event kind ${event.kind}`);
    }

    console.info(RecoveryPointsRepository.scannedRecoveryPoints.size);
}

function applyRecoveryPointHealthyEvent(event: Event): void {
    const id = event.getLabel("human_readable_recovery_point_id");

    RecoveryPointsRepository.scannedRecoveryPoints.set(id, {
        id,
        elastioAssetId: event.getLabel("cloud_connector_asset_id"),
        malwareDetected: false,
        ransomwareDetected: false,
        lastScanTime: event.eventTime,
    });
}

function applyRecoveryPointUnhealthyEvent(event: Event): void {
    const id = event.getLabel("human_readable_recovery_point_id");

    RecoveryPointsRepository.scannedRecoveryPoints.set(id, {
        id,
        elastioAssetId: event.getLabel("cloud_connector_asset_id"),
        malwareDetected: event.getLabel("number_of_malware_threats") > 0,
        ransomwareDetected: event.getLabel("number_of_ransomware_threats") > 0,
        lastScanTime: event.eventTime,
    });
}

