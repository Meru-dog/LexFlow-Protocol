/**
 * Development-only logging utility
 * In production, these are no-ops for better performance and security
 */

const isDevelopment = import.meta.env.DEV;

export const devLog = {
    log: (...args: any[]) => {
        if (isDevelopment) {
            console.log(...args);
        }
    },

    error: (...args: any[]) => {
        if (isDevelopment) {
            console.error(...args);
        }
    },

    warn: (...args: any[]) => {
        if (isDevelopment) {
            console.warn(...args);
        }
    },

    info: (...args: any[]) => {
        if (isDevelopment) {
            console.info(...args);
        }
    }
};

/**
 * Production-safe error reporting
 * Logs in development, could be extended to send to error tracking service in production
 */
export const reportError = (error: Error, context?: string) => {
    if (isDevelopment) {
        console.error(`Error${context ? ` in ${context}` : ''}:`, error);
    } else {
        // In production, you could send to Sentry, LogRocket, etc.
        // Example: Sentry.captureException(error, { tags: { context } });
    }
};
