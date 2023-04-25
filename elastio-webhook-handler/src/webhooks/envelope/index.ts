import {
    EnvelopeV0,
    processEnvelopeV0,
    V0,
    DeprecationWarning as DeprecationWarningV0,
    Event as EventV0,
} from './v0';

export interface Envelope {
    version: string;
}

export interface EnvelopeEventsHandler {
    onEnvelopeV0DeprecationWarning: ((dep_warning: DeprecationWarningV0) => void) | undefined;
    onEnvelopeV0EventDeprecationWarning: ((event: EventV0) => void) | undefined;
    onEnvelopeV0Event: ((event: any) => void) | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
}

/*
 * Validates the webhook payload and prints deprecation warnings if needed.
 * If it finds unsupported version of the payload, throws an error.
 *
 * If payload is valid, calls the appropriate handler for each event.
 */
export function processEnvelope(payload: Envelope, options: EnvelopeEventsHandler) {
    switch (payload.version) {
        case V0:
            return processEnvelopeV0(payload as EnvelopeV0, options);
        default:
            console.error(`You are trying to process Elastio Webhook payload of unsupported version ${payload.version}. ` +
                "Since the version has been changed, some breaking change was introduced.");

            throw new Error(`Unsupported webhook payload version ${payload.version}`);
    }
}
