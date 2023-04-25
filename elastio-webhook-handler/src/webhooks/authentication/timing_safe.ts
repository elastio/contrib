import * as crypto from 'crypto';

export function safeCompare(secret: string, preservedValue: Buffer, value: string): boolean {
    const encodedValue = encodeValue(secret, value);

    if (encodedValue.length !== preservedValue.length) {
        return false;
    }

    return crypto.timingSafeEqual(preservedValue, encodedValue);
}

export function encodeValue(secret: string, value: string): Buffer {
    const digest = crypto.createHmac('sha256', secret).update(value).digest("hex")
    return Buffer.from(digest);
}

export function generateSecret(): string {
    return crypto.randomBytes(32).toString('hex');
}
