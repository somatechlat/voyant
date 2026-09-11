package com.voyant.sdk;

/**
 * Exception thrown when the Voyant API returns a non-2xx response.
 */
public class VoyantAPIException extends Exception {

    private final int statusCode;
    private final String responseBody;

    public VoyantAPIException(int statusCode, String responseBody) {
        super(String.format("Voyant API error %d: %s", statusCode,
                responseBody != null && responseBody.length() > 200
                        ? responseBody.substring(0, 200) + "..."
                        : responseBody));
        this.statusCode = statusCode;
        this.responseBody = responseBody;
    }

    /** HTTP status code returned by the API. */
    public int getStatusCode() { return statusCode; }

    /** Raw response body from the API. */
    public String getResponseBody() { return responseBody; }
}
