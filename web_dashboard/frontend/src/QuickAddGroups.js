import React, { useState } from 'react';

const POPULAR_LISTS = {
  'NIFTY 50': ['2885', '3045', '1594', '11536', '1660', '1394', '4963', '2475', '3499', '10738'],
  'BANK NIFTY': ['1394', '4963', '17818', '2475', '317', '1901'],
  'High Volume': ['5097', '4503', '11351', '21690', '25049', '1594', '7229'],
};

const QuickAddGroups = ({ onAddGroup, currentTokens = [] }) => {
  const [adding, setAdding] = useState(null);

  const handleAdd = async (groupName) => {
    const tokens = POPULAR_LISTS[groupName];
    const newTokens = tokens.filter(t => !currentTokens.includes(t));

    if (newTokens.length === 0) {
      return { added: 0, skipped: tokens.length };
    }

    setAdding(groupName);
    let added = 0;
    for (const token of newTokens) {
      try {
        await onAddGroup(token);
        added++;
      } catch (e) {
        // continue with remaining tokens
      }
    }
    setAdding(null);
    return { added, skipped: tokens.length - newTokens.length };
  };

  return (
    <div className="quick-add-groups">
      <span className="quick-add-label">Quick add:</span>
      {Object.keys(POPULAR_LISTS).map(name => (
        <button
          key={name}
          className="quick-add-btn"
          onClick={() => handleAdd(name)}
          disabled={adding === name}
        >
          {adding === name ? 'Adding...' : `+ ${name}`}
        </button>
      ))}
    </div>
  );
};

export default QuickAddGroups;
