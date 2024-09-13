import math

# Cumulative distribution function for standard normal distribution (approximation)
def norm_cdf(x):
    """
    Approximate cumulative distribution function for a standard normal distribution.
    """
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

# Black-Scholes option pricing model for Call and Put
def black_scholes_option(S, K, T, r, sigma, option_type='call'):
    """
    Calculate the Black-Scholes option price.
    
    S: Current stock price
    K: Strike price
    T: Time to maturity (in years)
    r: Risk-free interest rate
    sigma: Volatility (standard deviation of stock returns)
    option_type: 'call' for Call option, 'put' for Put option
    """
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    
    if option_type == 'call':
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    elif option_type == 'put':
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
    else:
        raise ValueError("Invalid option type. Choose 'call' or 'put'.")
    
    return price

# Vega function (sensitivity of option price to volatility)
def vega(S, K, T, r, sigma):
    """
    Calculate vega, which is the derivative of the option price with respect to volatility.
    """
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return S * math.sqrt(T) * (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)

# Implied volatility calculation without using SciPy
def implied_volatility_option(S, K, T, r, market_price, option_type='call', tol=1e-5, max_iter=100):
    """
    Calculate the implied volatility using the market price of an option.
    
    S: Current stock price
    K: Strike price
    T: Time to maturity (in years)
    r: Risk-free interest rate
    market_price: Observed market price of the option
    option_type: 'call' for Call option, 'put' for Put option
    tol: Tolerance for the convergence of volatility
    max_iter: Maximum number of iterations for Newton-Raphson method
    """
    # Initial guess for volatility
    sigma = 0.2
    for i in range(max_iter):
        # Calculate the option price with the current guess for sigma
        price = black_scholes_option(S, K, T, r, sigma, option_type)
        # Calculate vega (rate of change of option price with volatility)
        v = vega(S, K, T, r, sigma)
        
        # Newton-Raphson step
        price_diff = price - market_price
        if abs(price_diff) < tol:
            return sigma
        sigma -= price_diff / v
    
    # If not converged, return the last estimate
    return sigma