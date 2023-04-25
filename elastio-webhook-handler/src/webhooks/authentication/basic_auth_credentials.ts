import {APIGatewayProxyEventV2} from "aws-lambda";

import {encodeValue, generateSecret, safeCompare} from "./timing_safe";

export class BasicAuthCredentials {
    private readonly secret: string;
    private readonly username: Buffer;
    private readonly password: Buffer;

    constructor(login: string, password: string) {
        this.secret = generateSecret();
        this.username = encodeValue(this.secret, login);
        this.password = encodeValue(this.secret, password);
    }

    authenticateRequest(req: APIGatewayProxyEventV2): boolean {
        const header = req.headers.authorization;
        if (header === undefined) {
            return false;
        }

        const headerParts = header.split('Basic ');
        if (headerParts.length !== 2) {
            return false;
        }

        const encoded = headerParts[1];

        const decoded = Buffer.from(encoded, 'base64').toString();
        const [username, password] = decoded.split(':');

        return safeCompare(this.secret, this.username, username) && safeCompare(this.secret, this.password, password);
    }
}

