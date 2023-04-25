# elastio-webhook-handler

This is an example Lambda function that demonstrates how to receive and process Elastio webhooks.

It's a simple example that focuses on processing a few types of events to gather information about Cyber Scanned Recovery Points.

The example includes an easy-to-use ENV-based configuration provider, but you can use any configuration source you prefer (such as AWS SSM) by implementing the ConfigProvider interface found in src/config/index.js.

If you're interested in using this Lambda function, we've included step-by-step instructions on how to use it with configuration taken from ENV variables.

## Prerequisites
- Node.js v18.0
- yarn

## Installation

```bash
yarn install
```

## Usage

### Authentication

This example support 3 methods of authentication available for Elastio Webhook (and can work without any of them):

- No Authorization
- Basic Auth - `Authorization` header with Base64 encoded username and password combination, preceded with `Basic` prefix,
- Bearer Token – `Authorization` with token preceded with `Bearer` prefix,
- Your own API-token – any header and any value as token.

Method of authentication will be selected automatically depending on provided configuration.

### No Authorization

Not recommended, but you can use it add environment variable:

```bash
ELASTIO_WEBHOOK_HANDLER_NO_AUTH=true
```


### Basic Auth

Setup username and password via ENV-variables:

```bash
ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_USERNAME=user
ELASTIO_WEBHOOK_HANDLER_BASIC_AUTH_PASSWORD=password1234
```

### Bearer Token

Setup bearer token with:

```bash
ELASTIO_WEBHOOK_HANDLER_BEARER_TOKEN=abc3afhureas
```

### Your own API-token

```bash
ELASTIO_WEBHOOK_HANDLER_API_TOKEN_KEY=X-API-TOKEN
ELASTIO_WEBHOOK_HANDLER_API_TOKEN_VALUE=abc3afhureas
```

## Build

```bash
npm install --global yarn
yarn install
yarn run build
```

Then the project will be compiled into`dist/index.mjs`, that can be uploaded to AWS Lambda.

## Adding your business logic

Lambda passes webhook payload (envelope) to the `processEnvelope` function. It accepts an object with
several callbacks. You can specify what to do in case of deprecation of single event or envelope in total.
And also you can specify what to do with each event in the envelope.
