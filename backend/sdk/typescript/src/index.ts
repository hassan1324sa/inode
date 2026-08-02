export const SDK_VERSION = "1.3.0";
export const MINIMUM_SUPPORTED_SERVER_VERSION = "1.0.0";

export interface CredentialOptions {
  apiKey?: string;
  bearerToken?: string;
  customHeaders?: Record<string, string>;
}

export interface ClientOptions {
  baseUrl?: string;
  credential?: CredentialOptions;
  serverVersion?: string;
}

export class VersionIncompatibleError extends Error {
  constructor(public sdkVersion: string, public serverVersion: string, public minSupported: string) {
    super(
      `SDK version ${sdkVersion} is incompatible with server version ${serverVersion}. Minimum supported is ${minSupported}.`
    );
    this.name = "VersionIncompatibleError";
  }
}

export class FluxaClient {
  public baseUrl: string;
  public sdkVersion: string = SDK_VERSION;
  public serverVersion: string;
  public minSupportedServerVersion: string = MINIMUM_SUPPORTED_SERVER_VERSION;

  constructor(options: ClientOptions = {}) {
    this.baseUrl = options.baseUrl || "http://localhost:8000";
    this.serverVersion = options.serverVersion || "1.3.0";
  }

  public verifyCompatibility(): boolean {
    // Basic semver check
    if (this.serverVersion < this.minSupportedServerVersion) {
      throw new VersionIncompatibleError(
        this.sdkVersion,
        this.serverVersion,
        this.minSupportedServerVersion
      );
    }
    return true;
  }
}
