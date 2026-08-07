import request from './request'

export const getStatus = () => request.get('/status')
