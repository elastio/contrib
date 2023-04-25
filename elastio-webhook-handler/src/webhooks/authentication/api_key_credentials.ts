import {APIGatewayProxyEventV2} from "aws-lambda";

import {encodeValue, generateSecret, safeCompare} from "./timing_safe";

export class ApiKeyCredentials {
    private readonly secret: string;
    private readonly key: string;
    private readonly value: Buffer;

    constructor(key: string, value: string) {
        this.secret = generateSecret();
        this.key = key.toLowerCase(); // Node.js converts all header names to lower case
        this.value = encodeValue(this.secret, value);
    }

    authenticateRequest(req: APIGatewayProxyEventV2): boolean {
        const value = req.headers[this.key];

        if (!value) {
            return false;
        }

        return safeCompare(this.secret, this.value, value);
    }
}
