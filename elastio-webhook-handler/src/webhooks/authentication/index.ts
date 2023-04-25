import {APIGatewayProxyEventV2} from "aws-lambda";

import {BasicAuthCredentials} from "./basic_auth_credentials";
import {BearerTokenCredentials} from "./bearer_token";
import {ApiKeyCredentials} from "./api_key_credentials";
import {NullCredentials} from "./null_credentials";

interface Credentials {
    authenticateRequest(req: APIGatewayProxyEventV2): boolean
}

export {BasicAuthCredentials, BearerTokenCredentials, ApiKeyCredentials, NullCredentials, Credentials};
