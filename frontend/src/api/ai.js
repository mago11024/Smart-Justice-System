import api from './index'

export function searchSimilarCases(query, topK = 5) {
  return api.get('/ai/similar-cases', { params: { q: query, top_k: topK }, timeout: 30000 })
}

export function getAIEngines() {
  return api.get('/ai/engines')
}

export function switchEngine(engine) {
  return api.post('/ai/engines/switch', { engine })
}
