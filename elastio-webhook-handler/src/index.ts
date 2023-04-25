import {APIGatewayProxyEventV2} from "aws-lambda";


import {Config} from "./config";
import {EnvConfigProvider} from "./config/env_config_provider";
import {processEnvelope} from "./webhooks"
import {Envelope} from "./webhooks/envelope";
import {DeprecationWarning as DeprecationWarningV0, Event as EventV0} from "./webhooks/envelope/v0";
import {processEvent} from "./example";

const config = new Config(new EnvConfigProvider());
const credentials = config.authCredentials();

export enum StatusCode {
    Ok = 200,
    BadRequest = 400,
    Unauthorized = 401,
    NotFound = 404,
    UnprocessableContent = 422,
    Internal = 500,
}



export async function handler(event: APIGatewayProxyEventV2): Promise<any> { // eslint-disable-line @typescript-eslint/no-explicit-any
    const contentType = event.headers['content-type'];
    if (contentType !== 'application/json') {
        console.warn('invalid content type');
        return {
            statusCode: StatusCode.BadRequest,
            body: 'expecting Content-Type application/json'
        };
    }

    if (!credentials.authenticateRequest(event)) {
        console.warn('invalid credentials');
        return {
            statusCode: StatusCode.Unauthorized,
            body: 'Unauthenticated'
        };
    }

    if (!event.body) {
        console.warn('invalid request body');
        return {
            statusCode: StatusCode.BadRequest,
            body: 'invalid request body'
        };
    }

    let body;

    try {
        body = JSON.parse(event.body);
    } catch (e) {
        console.warn(`invalid request body: ${e}`);
        return {
            statusCode: StatusCode.BadRequest,
            body: 'invalid request body'
        };
    }


    try {
        processEnvelope(
            body as Envelope,
            {
                onEnvelopeV0DeprecationWarning: (warning: DeprecationWarningV0) => {
                    console.warn(warning);

                    // TODO: Process deprecation warning: send error to Airbrake or Sentry, etc.
                },
                onEnvelopeV0EventDeprecationWarning: (event: EventV0) => {
                    console.warn(event.kind, event.deprecation_warning);
                    // TODO: Process deprecation warning: send error to Airbrake or Sentry, etc.
                },
                onEnvelopeV0Event: processEvent,
            });

        return { statusCode: StatusCode.Ok, body: {} };
    } catch (e) {
        return { statusCode: StatusCode.UnprocessableContent, body: "can't process webhook payload" };
    }
}
