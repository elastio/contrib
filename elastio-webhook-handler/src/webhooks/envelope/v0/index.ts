export interface EnvelopeV0 {
    version: string;
    deprecation_warning: DeprecationWarning | null;
    events: Array<Event>;
}

export interface Event {
    deprecation_warning: DeprecationWarning | null;
    kind: string,
    version: string,
}

export interface DeprecationWarning {
    notice: string;
    effective_date: string;
}

export const V0 = "v0";

interface EnvelopeV0EventsHandler {
    onEnvelopeV0DeprecationWarning: ((dep_warning: DeprecationWarning) => void) | undefined;
    onEnvelopeV0EventDeprecationWarning: ((event: Event) => void) | undefined;
    onEnvelopeV0Event: ((event: any) => void) | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
}

export function processEnvelopeV0(payload: EnvelopeV0, options: EnvelopeV0EventsHandler): void {
    if (payload.deprecation_warning) {
        console.warn(`You are trying to process Elastio Webhook payload of a version ${payload.version} ` +
            `that will be deprecated after ${payload.deprecation_warning.effective_date}. ` +
            "Please ensure that you are ready to receive payload of newer version. " +
            `Details: ${payload.deprecation_warning.notice}`);

        options.onEnvelopeV0DeprecationWarning?.call(null, payload.deprecation_warning);
    }

    for (const event of payload.events) {
        if (event.deprecation_warning) {
            console.warn(`You are trying to process Elastio event of a version ${event.version} ` +
                `that will be deprecated after ${event.deprecation_warning.effective_date}. ` +
                "Please ensure that you are ready to receive payload of newer version. " +
                `Details: ${event.deprecation_warning.notice}`);

            options.onEnvelopeV0EventDeprecationWarning?.call(null, event);
        }

        options.onEnvelopeV0Event?.call(null, event);
    }
}
