import {APIGatewayProxyEventV2} from "aws-lambda";

import {encodeValue, generateSecret, safeCompare} from "./timing_safe";

export class BearerTokenCredentials {
    private readonly secret: string;
    private readonly token: Buffer;

    constructor(token: string) {
        this.secret = generateSecret();
        this.token = encodeValue(this.secret, token);
    }

    authenticateRequest(req: APIGatewayProxyEventV2): boolean {
        const header = req.headers.authorization;
        if (header === undefined) {
            return false;
        }

        const headerParts = header.split('Bearer ');
        if (headerParts.length !== 2) {
            return false;
        }

        const token = headerParts[1];

        return safeCompare(this.secret, this.token, token);
    }
}
