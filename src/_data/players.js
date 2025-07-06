const fs = require('fs');
const path = require('path');

module.exports = function() {
  // Read the manifest file
  const manifestPath = path.join(__dirname, 'players', 'manifest.json');
  if (!fs.existsSync(manifestPath)) {
    console.warn('Players manifest file not found:', manifestPath);
    return { items: [], getPlayer: () => null, getPlayerName: () => 'Unknown Player' };
  }

  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (!manifest || typeof manifest !== 'object' || !manifest.players) {
      console.error('Invalid manifest file structure');
      return { items: [], getPlayer: () => null, getPlayerName: () => 'Unknown Player' };
    }
  } catch (error) {
    console.error('Error parsing manifest file:', error);
    return { items: [], getPlayer: () => null, getPlayerName: () => 'Unknown Player' };
  }

  // Create a map to cache loaded chunks
  const chunkCache = new Map();

  // Function to load a chunk
  function loadChunk(chunkNum) {
    if (!chunkCache.has(chunkNum)) {
      const chunkPath = path.join(__dirname, 'players', `chunk_${chunkNum}.json`);
      if (!fs.existsSync(chunkPath)) {
        console.warn('Player chunk file not found:', chunkPath);
        chunkCache.set(chunkNum, []);
        return [];
      }
      try {
        const chunk = JSON.parse(fs.readFileSync(chunkPath, 'utf8'));
        if (!Array.isArray(chunk)) {
          console.error('Invalid chunk data structure:', chunkPath);
          chunkCache.set(chunkNum, []);
          return [];
        }
        chunkCache.set(chunkNum, chunk);
      } catch (error) {
        console.error('Error loading player chunk:', chunkPath, error);
        chunkCache.set(chunkNum, []);
        return [];
      }
    }
    return chunkCache.get(chunkNum) || [];
  }

  // Return an object with the player IDs array and helper functions
  return {
    items: Object.keys(manifest.players),
    getPlayer: function(playerId) {
      const playerInfo = manifest.players[playerId];
      if (!playerInfo) return null;

      const chunk = loadChunk(playerInfo.chunk);
      return chunk.find(p => p.id === playerId) || null;
    },
    getPlayerName: function(playerId) {
      const playerInfo = manifest.players[playerId];
      return playerInfo ? playerInfo.name : 'Unknown Player';
    }
  };
};