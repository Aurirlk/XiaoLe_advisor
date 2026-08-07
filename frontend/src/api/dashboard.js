import request from './request'

export const getSummary = () => request.get('/api/dashboard/summary')
export const getFunnel = () => request.get('/api/dashboard/funnel')
