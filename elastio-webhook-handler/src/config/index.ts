import {ApiKeyCredentials, BasicAuthCredentials, BearerTokenCredentials, NullCredentials, Credentials} from "../webhooks/authentication";

/**
 * ConfigProvider is an abstraction over configuration source. Default implementation is ENV-based,
 * but you are welcome to implement any other provider: AWS SSM, file, etc.
 *
 * TODO: add other provider, for example AWS SSM, if it's needed
 */
export interface ConfigProvider {
    /**
     * If you are going to use API Key authentication method, ConfigProvider should contain a header name for such token.
     *
     * Let's assume you want to use `X-USER-API-TOKEN` header, then provider must return `X-USER-API-TOKEN`
     * (see {@link apiKeyValue} to check how to specify token itself:
     * ~~~
     * POST /process_webhook HTTP/1.1
     * X-USER-API-TOKEN: a1b2c3d4e5f6g7h8i9j0
     *
     * ~~~
     */
    apiKeyName(): string | null;

    /**
     * If you are going to use API Key authentication method, ConfigProvider should contain a token.
     *
     * Let's assume you want to use `a1b2c3d4e5f6g7h8i9j0` as token, specified in header (see {@link apiKeyName}),
     * then provider must return `a1b2c3d4e5f6g7h8i9j0`:
     *
     * ~~~
     * POST /process_webhook HTTP/1.1
     * X-USER-API-TOKEN: a1b2c3d4e5f6g7h8i9j0
     *
     * ~~~
     */
    apiKeyValue(): string | null;

    /**
     * If you are going to use Bearer authentication method, ConfigProvider should contain a token.
     *
     * Let's assume you want to use `a1b2c3d4e5f6g7h8i9j0` as token, specified in header:
     *
     * ~~~
     * POST /process_webhook HTTP/1.1
     * AUTHENTICATION: Bearer a1b2c3d4e5f6g7h8i9j0
     *
     * ~~~
     */
    bearerToken(): string | null;

    /**
     * If you are going to use Basic Auth authentication method, ConfigProvider should contain a username.
     */
    basicAuthUsername(): string | null;

    /**
     * If you are going to use Basic Auth authentication method, ConfigProvider should contain a password.
     */
    basicAuthPassword(): string | null;

    /**
     * If you are going to use no authentication method, ConfigProvider should return `true`.
     */
    noAuth(): boolean;
}

/**
 * Extracts configuration from ConfigProvider. If some configuration is not provided, it will use default values.
 */
export class Config {
    private provider: ConfigProvider;

    constructor(provider: ConfigProvider) {
        this.provider = provider;
    }

    authCredentials(): Credentials {
        const apiToken = this.apiToken();
        if (apiToken !== null) {
            console.info("using `API Key` auth method");
            return new ApiKeyCredentials(apiToken.headerName, apiToken.key);
        }

        console.warn("cannot use `API Key` auth method: no credentials provided");

        const bearerToken = this.bearerToken();
        if (bearerToken !== null) {
            console.info("using `Bearer` auth method");
            return new BearerTokenCredentials(bearerToken);
        }

        console.warn("cannot use `Bearer` auth method: no credentials provided");

        const basicAuth = this.basicAuth();
        if (basicAuth !== null) {
            console.info("using `Basic Auth` auth method");
            return new BasicAuthCredentials(basicAuth.username, basicAuth.password);
        }

        console.warn("cannot use `Basic Auth` auth method: no credentials provided");

        if (this.provider.noAuth()) {
            console.warn("starting without authentication");
            return new NullCredentials();
        }

        throw new Error("cannot start: no authentication method provided");
    }

    private apiToken(): ApiKeyConfig | null {
        const key = this.provider.apiKeyName();
        const value = this.provider.apiKeyValue();

        if (key === null || value === null) {
            return null;
        }

        return {
            headerName: key,
            key: value
        }
    }

    private bearerToken(): string | null {
        return this.provider.bearerToken();
    }

    private basicAuth(): BasicAuthConfig | null {
        const username = this.provider.basicAuthUsername();
        const password = this.provider.basicAuthPassword();

        if (username === null || password === null) {
            return null;
        }

        return {
            username: username,
            password: password
        }
    }
}

interface ApiKeyConfig {
    headerName: string;
    key: string;
}

interface BasicAuthConfig {
    username: string;
    password: string;
}
