import React from 'react';

const formatVolume = (volume) => {
  if (!volume) return '-';
  if (volume >= 10000000) return `${(volume / 10000000).toFixed(1)}Cr`;
  if (volume >= 100000) return `${(volume / 100000).toFixed(1)}L`;
  return volume.toLocaleString();
};

const WatchlistCards = ({ watchlist, onRemove, onSelect }) => {
  if (watchlist.length === 0) {
    return (
      <div className="cards-empty">
        <p>No stocks in watchlist</p>
      </div>
    );
  }

  return (
    <div className="watchlist-cards">
      {watchlist.map(stock => {
        const change = stock.change_percent || 0;
        const changeClass = change >= 0 ? 'positive' : 'negative';

        return (
          <div
            key={stock.token}
            className="stock-card"
            onClick={() => onSelect && onSelect(stock)}
          >
            <div className="card-header">
              <div className="card-stock-info">
                <span className="card-symbol">{stock.symbol}</span>
                <span className="card-token">{stock.token}</span>
              </div>
              <button
                className="card-remove-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(stock.token);
                }}
                title="Remove"
              >
                x
              </button>
            </div>

            <div className="card-price-row">
              <span className="card-ltp">
                {stock.ltp ? `₹${stock.ltp.toFixed(2)}` : '-'}
              </span>
              <span className={`card-change ${changeClass}`}>
                {change >= 0 ? '+' : ''}{change.toFixed(2)}%
              </span>
            </div>

            <div className="card-details">
              <div className="card-detail">
                <span className="card-detail-label">Volume</span>
                <span className="card-detail-value">{formatVolume(stock.volume)}</span>
              </div>
              <div className="card-detail">
                <span className="card-detail-label">RSI</span>
                <span className={`card-detail-value ${stock.rsi14 > 70 ? 'rsi-high' : stock.rsi14 < 30 ? 'rsi-low' : ''}`}>
                  {stock.rsi14 ? stock.rsi14.toFixed(1) : '-'}
                </span>
              </div>
              <div className="card-detail">
                <span className="card-detail-label">VWAP</span>
                <span className="card-detail-value">
                  {stock.vwap ? `₹${stock.vwap.toFixed(2)}` : '-'}
                </span>
              </div>
            </div>

            {stock.alert && (
              <div className="card-alert">
                {stock.alert}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default WatchlistCards;
