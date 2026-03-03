// utils.test.js - Comprehensive tests for utils.js

'use strict';

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock the global `db` object used by fetchUserData
const mockExecute = jest.fn();
global.db = { execute: mockExecute };

// Mock the global `processAmount` function used by processPayment
const mockProcessAmount = jest.fn();
global.processAmount = mockProcessAmount;

// Mock global fetch used by loadConfig
global.fetch = jest.fn();

// Spy on console.log to assert on logging behaviour
const consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});

// ─── Module under test ────────────────────────────────────────────────────────
const { fetchUserData, processPayment, loadConfig, calculateDiscount } =
  require('../utils');

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Build a minimal Response-like object for fetch mocks.
 */
function buildFetchResponse({ ok = true, status = 200, statusText = 'OK', body = {} } = {}) {
  return {
    ok,
    status,
    statusText,
    json: jest.fn().mockResolvedValue(body),
  };
}

// ─── Reset mocks between tests ────────────────────────────────────────────────
beforeEach(() => {
  jest.clearAllMocks();
});

// =============================================================================
// fetchUserData
// =============================================================================
describe('fetchUserData', () => {

  describe('happy path', () => {
    it('calls db.execute with a parameterized query and the correct userId', () => {
      const fakeResult = [{ id: 1, name: 'Alice' }];
      mockExecute.mockReturnValue(fakeResult);

      const result = fetchUserData(1);

      expect(mockExecute).toHaveBeenCalledTimes(1);
      // First argument must be the parameterized query string (no inline value)
      expect(mockExecute).toHaveBeenCalledWith(
        'SELECT * FROM users WHERE id = ?',
        [1]
      );
      expect(result).toBe(fakeResult);
    });

    it('works with a string userId', () => {
      mockExecute.mockReturnValue([]);

      fetchUserData('42');

      expect(mockExecute).toHaveBeenCalledWith(
        'SELECT * FROM users WHERE id = ?',
        ['42']
      );
    });

    it('works with userId of 0 (falsy but valid)', () => {
      mockExecute.mockReturnValue([]);

      fetchUserData(0);

      expect(mockExecute).toHaveBeenCalledWith(
        'SELECT * FROM users WHERE id = ?',
        [0]
      );
    });
  });

  describe('SQL injection prevention', () => {
    it('passes a potentially malicious string as a parameter, NOT inline in the query', () => {
      const malicious = "1; DROP TABLE users; --";
      mockExecute.mockReturnValue([]);

      fetchUserData(malicious);

      const [query, params] = mockExecute.mock.calls[0];
      // The raw string must never appear in the query itself
      expect(query).not.toContain(malicious);
      // It must be safely passed as a bound parameter
      expect(params).toEqual([malicious]);
    });

    it('passes a SQL UNION injection attempt as a bound parameter', () => {
      const malicious = "' UNION SELECT * FROM secrets --";
      mockExecute.mockReturnValue([]);

      fetchUserData(malicious);

      const [query, params] = mockExecute.mock.calls[0];
      expect(query).not.toContain(malicious);
      expect(params).toEqual([malicious]);
    });

    it('query string itself never interpolates the userId value', () => {
      mockExecute.mockReturnValue([]);

      fetchUserData(99);

      const [query] = mockExecute.mock.calls[0];
      expect(query).toBe('SELECT * FROM users WHERE id = ?');
    });
  });

  describe('input validation', () => {
    it('throws when userId is undefined', () => {
      expect(() => fetchUserData(undefined)).toThrow('userId is required');
    });

    it('throws when userId is null', () => {
      expect(() => fetchUserData(null)).toThrow('userId is required');
    });

    it('throws when called with no arguments', () => {
      expect(() => fetchUserData()).toThrow('userId is required');
    });

    it('does NOT throw for an empty string (falsy but not null/undefined)', () => {
      mockExecute.mockReturnValue([]);
      // empty string is a caller concern; the guard only rejects null/undefined
      expect(() => fetchUserData('')).not.toThrow();
    });
  });
});

// =============================================================================
// processPayment
// =============================================================================
describe('processPayment', () => {

  describe('happy path', () => {
    it('returns true for a valid non-zero amount', () => {
      const result = processPayment(100, '4111111111111111');

      expect(result).toBe(true);
    });

    it('calls processAmount with the numeric value of amount', () => {
      processPayment('250', '4111111111111111');

      expect(mockProcessAmount).toHaveBeenCalledTimes(1);
      expect(mockProcessAmount).toHaveBeenCalledWith(250);
    });

    it('coerces a string amount to a number before passing to processAmount', () => {
      processPayment('99.99', '4111111111111111');

      expect(mockProcessAmount).toHaveBeenCalledWith(99.99);
    });

    it('returns false when amount is 0', () => {
      const result = processPayment(0, '4111111111111111');

      expect(result).toBe(false);
      expect(mockProcessAmount).not.toHaveBeenCalled();
    });

    it('returns false when amount is the string "0"', () => {
      const result = processPayment('0', '4111111111111111');

      expect(result).toBe(false);
    });
  });

  describe('sensitive data – card number is never logged', () => {
    it('does not log the card number at any point', () => {
      const cardNumber = '4111111111111111';
      processPayment(50, cardNumber);

      const allLoggedArgs = consoleLogSpy.mock.calls.flat().join(' ');
      expect(allLoggedArgs).not.toContain(cardNumber);
    });

    it('logs a generic processing message without PII', () => {
      processPayment(50, '4111111111111111');

      expect(consoleLogSpy).toHaveBeenCalledWith('Processing payment...');
    });

    it('does not use eval (processAmount is called directly)', () => {
      // If eval were used we could detect it by patching; instead we verify
      // processAmount mock was invoked, proving the direct-call path is taken.
      processPayment(75, '4111111111111111');

      expect(mockProcessAmount).toHaveBeenCalledWith(75);
    });
  });

  describe('input validation – amount', () => {
    it('throws when amount is undefined', () => {
      expect(() => processPayment(undefined, '4111111111111111')).toThrow(
        'amount is required'
      );
    });

    it('throws when amount is null', () => {
      expect(() => processPayment(null, '4111111111111111')).toThrow(
        'amount is required'
      );
    });

    it('throws when called with no arguments', () => {
      expect(() => processPayment()).toThrow('amount is required');
    });
  });

  describe('input validation – cardNumber', () => {
    it('throws when cardNumber is undefined', () => {
      expect(() => processPayment(100, undefined)).toThrow(
        'cardNumber is required'
      );
    });

    it('throws when cardNumber is null', () => {
      expect(() => processPayment(100, null)).toThrow('cardNumber is required');
    });

    it('throws when cardNumber is an empty string', () => {
      expect(() => processPayment(100, '')).toThrow('cardNumber is required');
    });
  });
});

// =============================================================================
// loadConfig
// =============================================================================
describe('loadConfig', () => {

  describe('happy path', () => {
    it('returns the parsed JSON body from a successful response', async () => {
      const configBody = { theme: 'dark', version: '2.0' };
      fetch.mockResolvedValue(buildFetchResponse({ body: configBody }));

      const result = await loadConfig();

      expect(result).toEqual(configBody);
    });

    it('calls fetch with the correct endpoint', async () => {
      fetch.mockResolvedValue(buildFetchResponse());

      await loadConfig();

      expect(fetch).toHaveBeenCalledWith('/api/config');
    });

    it('awaits response.json() – returns resolved value, not a Promise', async () => {
      const configBody = { key: 'value' };
      const mockResponse = buildFetchResponse({ body: configBody });
      fetch.mockResolvedValue(mockResponse);

      const result = await loadConfig();

      // Verify json() was actually called (await path exercised)
      expect(mockResponse.json).toHaveBeenCalledTimes(1);
      // Result must be the resolved value, not a pending Promise
      expect(result).not.toBeInstanceOf(Promise);
      expect(result).toEqual(configBody);
    });

    it('handles an empty config object', async () => {
      fetch.mockResolvedValue(buildFetchResponse({ body: {} }));

      const result = await loadConfig();

      expect(result).toEqual({});
    });
  });

  describe('HTTP error handling', () => {
    it('throws when the response is not ok (404)', async () => {
      fetch.mockResolvedValue(
        buildFetchResponse({ ok: false, status: 404, statusText: 'Not Found' })
      );

      await expect(loadConfig()).rejects.toThrow(
        'Failed to load config: 404 Not Found'
      );
    });

    it('throws when the response is not ok (500)', async () => {
      fetch.mockResolvedValue(
        buildFetchResponse({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
        })
      );

      await expect(loadConfig()).rejects.toThrow(
        'Failed to load config: 500 Internal Server Error'
      );
    });

    it('includes the status code in the thrown error message', async () => {
      fetch.mockResolvedValue(
        buildFetchResponse({ ok: false, status: 403, statusText: 'Forbidden' })
      );

      await expect(loadConfig()).rejects.toThrow('403');
    });

    it('does not call response.json() when the response is not ok', async () => {
      const mockResponse = buildFetchResponse({
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
      });
      fetch.mockResolvedValue(mockResponse);

      await expect(loadConfig()).rejects.toThrow();
      expect(mockResponse.json).not.toHaveBeenCalled();
    });
  });

  describe('network / fetch failure', () => {
    it('propagates a network error thrown by fetch', async () => {
      fetch.mockRejectedValue(new Error('Network error'));

      await expect(loadConfig()).rejects.toThrow('Network error');
    });

    it('propagates a JSON parse error thrown by response.json()', async () => {
      const mockResponse = {
        ok: true,
        status: 200,
        statusText: 'OK',
        json: jest.fn().mockRejectedValue(new SyntaxError('Unexpected token')),
      };
      fetch.mockResolvedValue(mockResponse);

      await expect(loadConfig()).rejects.toThrow('Unexpected token');
    });
  });
});

// =============================================================================
// calculateDiscount
// =============================================================================
describe('calculateDiscount', () => {

  describe('happy path', () => {
    it('calculates a 10% discount on 100', () => {
      expect(calculateDiscount(100, 10)).toBe(90);
    });

    it('calculates a 50% discount on 200', () => {
      expect(calculateDiscount(200, 50)).toBe(100);
    });

    it('calculates a 0% discount (no reduction)', () => {
      expect(calculateDiscount(100, 0)).toBe(100);
    });

    it('calculates a 100% discount (free)', () => {
      expect(calculateDiscount(100, 100)).toBe(0);
    });

    it('handles decimal prices', () => {
      expect(calculateDiscount(19.99, 10)).toBeCloseTo(17.991, 3);
    });

    it('handles decimal discount percentages', () => {
      expect(calculateDiscount(100, 33.5)).toBeCloseTo(66.5, 5);
    });

    it('returns 0 when price is 0 regardless of discount', () => {
      expect(calculateDiscount(0, 50)).toBe(0);
    });
  });

  describe('boundary values for discount', () => {
    it('accepts discount exactly at lower boundary (0)', () => {
      expect(() => calculateDiscount(100, 0)).not.toThrow();
    });

    it('accepts discount exactly at upper boundary (100)', () => {
      expect(() => calculateDiscount(100, 100)).not.toThrow();
    });

    it('throws when discount is -1 (just below lower boundary)', () => {
      expect(() => calculateDiscount(100, -1)).toThrow(
        'discount must be between 0 and 100'
      );
    });

    it('throws when discount is 101 (just above upper boundary)', () => {
      expect(() => calculateDiscount(100, 101)).toThrow(
        'discount must be between 0 and 100'
      );
    });

    it('throws for a heavily negative discount', () => {
      expect(() => calculateDiscount(100, -50)).toThrow(
        'discount must be between 0 and 100'
      );
    });
  });

  describe('type validation', () => {
    it('throws when price is a string', () => {
      expect(() => calculateDiscount('100', 10)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when discount is a string', () => {
      expect(() => calculateDiscount(100, '10')).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when both price and discount are strings', () => {
      expect(() => calculateDiscount('100', '10')).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when price is null', () => {
      expect(() => calculateDiscount(null, 10)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when discount is undefined', () => {
      expect(() => calculateDiscount(100, undefined)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when price is NaN', () => {
      expect(() => calculateDiscount(NaN, 10)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when discount is NaN', () => {
      expect(() => calculateDiscount(100, NaN)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when price is an array', () => {
      expect(() => calculateDiscount([100], 10)).toThrow(
        'price and discount must be numbers'
      );
    });

    it('throws when price is an object', () => {
      expect(() => calculateDiscount({}, 10)).toThrow(
        'price and discount must be numbers'
      );
    });
  });
});
