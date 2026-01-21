import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Custom hook for polling with exponential backoff
 *
 * @param {Function} pollFn - Async function to execute on each poll
 * @param {boolean} shouldPoll - Boolean to start/stop polling
 * @param {Function} onComplete - Callback when poll returns complete status
 * @param {Function} onError - Callback when poll encounters error
 * @param {Object} options - Configuration options
 * @param {number} options.initialDelay - Initial delay in ms (default: 1000)
 * @param {number} options.maxDelay - Maximum delay in ms (default: 8000)
 * @param {number} options.backoffMultiplier - Multiplier for each iteration (default: 2)
 * @returns {Object} - { status, reset }
 */
export function useExponentialBackoff(
  pollFn,
  shouldPoll,
  onComplete,
  onError,
  options = {}
) {
  const {
    initialDelay = 1000,
    maxDelay = 8000,
    backoffMultiplier = 2
  } = options;

  const [status, setStatus] = useState(null);
  const timeoutRef = useRef(null);
  const currentDelayRef = useRef(initialDelay);
  const previousShouldPollRef = useRef(shouldPoll);

  // Reset function to reset backoff to initial delay
  const reset = useCallback(() => {
    currentDelayRef.current = initialDelay;
    setStatus(null);
  }, [initialDelay]);

  // Detect when shouldPoll changes from false to true (reset backoff)
  useEffect(() => {
    if (shouldPoll && !previousShouldPollRef.current) {
      // shouldPoll changed from false to true - reset backoff
      reset();
    }
    previousShouldPollRef.current = shouldPoll;
  }, [shouldPoll, reset]);

  useEffect(() => {
    // Cleanup function
    const cleanup = () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
    };

    // If polling should not happen, cleanup and exit
    if (!shouldPoll) {
      cleanup();
      return;
    }

    // Polling function with exponential backoff
    const poll = async () => {
      try {
        const result = await pollFn();
        setStatus(result);

        // Check if polling is complete
        if (result?.status === 'complete') {
          cleanup();
          if (onComplete) {
            onComplete(result);
          }
          return;
        }

        // Check if there's an error
        if (result?.status === 'error') {
          cleanup();
          if (onError) {
            onError(result);
          }
          return;
        }

        // Schedule next poll with exponential backoff
        const nextDelay = Math.min(
          currentDelayRef.current * backoffMultiplier,
          maxDelay
        );
        currentDelayRef.current = nextDelay;

        timeoutRef.current = setTimeout(poll, currentDelayRef.current);
      } catch (error) {
        cleanup();
        if (onError) {
          onError(error);
        }
      }
    };

    // Start first poll with initial delay
    timeoutRef.current = setTimeout(poll, currentDelayRef.current);

    // Cleanup on unmount or when dependencies change
    return cleanup;
  }, [shouldPoll, pollFn, onComplete, onError, backoffMultiplier, maxDelay]);

  return { status, reset };
}
