import React, { useState, useEffect, useRef } from 'react';

const TokenSearch = ({ onSelect, apiUrl, existingTokens = [] }) => {
  const [searchText, setSearchText] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchRef = useRef(null);
  const timeoutRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearch = (query) => {
    setSearchText(query);
    clearTimeout(timeoutRef.current);

    if (query.length < 2) {
      setResults([]);
      setShowDropdown(false);
      return;
    }

    setIsLoading(true);
    timeoutRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${apiUrl}/api/symbols/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        const symbols = (data.symbols || []).filter(s => !existingTokens.includes(s.token));
        setResults(symbols.slice(0, 8));
        setShowDropdown(true);
      } catch (e) {
        console.error('Search error:', e);
      } finally {
        setIsLoading(false);
      }
    }, 300);
  };

  const handleSelect = (stock) => {
    setSearchText('');
    setResults([]);
    setShowDropdown(false);
    onSelect(stock.token, stock.symbol);
  };

  return (
    <div className="token-search" ref={searchRef}>
      <div className="token-search-input-wrapper">
        <svg className="token-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          type="text"
          className="token-search-input"
          placeholder="Search by company name or token..."
          value={searchText}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => results.length > 0 && setShowDropdown(true)}
        />
        {isLoading && <span className="token-search-loading">...</span>}
      </div>

      {showDropdown && results.length > 0 && (
        <div className="token-search-dropdown">
          {results.map(stock => (
            <div
              key={stock.token}
              className="token-search-item"
              onClick={() => handleSelect(stock)}
            >
              <span className="token-search-symbol">{stock.symbol}</span>
              <span className="token-search-token">{stock.token}</span>
            </div>
          ))}
        </div>
      )}

      {showDropdown && results.length === 0 && searchText.length >= 2 && !isLoading && (
        <div className="token-search-dropdown">
          <div className="token-search-empty">No symbols found</div>
        </div>
      )}
    </div>
  );
};

export default TokenSearch;
