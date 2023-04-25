import {ConfigProvider} from "./index";

export class EnvConfigProvider implements ConfigProvider {
    noAuth(): boolean {
        const maybeNoAuth = process.env.ELASTIO_WEBHOOK_HANDLER_NO_AUTH;
        if (maybeNoAuth === undefined || maybeNoAuth === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_NO_AUTH is not set");
            return false;
        }

        return maybeNoAuth === "true";
    }

    apiKeyName(): string | null {
        const maybeApiTokenKey = process.env.ELASTIO_WEBHOOK_HANDLER_API_TOKEN_KEY;
        if (maybeApiTokenKey === undefined || maybeApiTokenKey === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_API_TOKEN_KEY is not set");
            return null;
        }

        return maybeApiTokenKey;
    }

    apiKeyValue(): string | null {
        const maybeApiTokenValue = process.env.ELASTIO_WEBHOOK_HANDLER_API_TOKEN_VALUE;
        if (maybeApiTokenValue === undefined || maybeApiTokenValue === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_API_TOKEN_VALUE is not set");
            return null;
        }

        return maybeApiTokenValue;
    }

    basicAuthPassword(): string | null {
        const maybeBasicAuthPassword = process.env.ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_PASSWORD;
        if (maybeBasicAuthPassword === undefined || maybeBasicAuthPassword === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_PASSWORD is not set");
            return null;
        }

        return maybeBasicAuthPassword;
    }

    basicAuthUsername(): string | null {
        const maybeBasicAuthUsername = process.env.ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_USERNAME;
        if (maybeBasicAuthUsername === undefined || maybeBasicAuthUsername === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_USERNAME is not set");
            return null;
        }

        return maybeBasicAuthUsername;
    }

    bearerToken(): string | null {
        const maybeBearerToken = process.env.ELASTIO_WEBHOOK_HANDLER_BEARER_TOKEN;
        if (maybeBearerToken === undefined || maybeBearerToken === "") {
            console.warn("ELASTIO_WEBHOOK_HANDLER_BEARER_TOKEN is not set");
            return null;
        }

        return maybeBearerToken;
    }
}
