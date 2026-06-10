import axios from 'axios'
import { API_BASE_URL } from '@/config'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
})

export const uploadCert = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/api/upload/cert', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const startValuation = (data) => {
  return apiClient.post('/api/valuation', data)
}

export const getHistory = (username) => {
  return apiClient.get('/api/history', { params: { username } })
}

export const getReportDetail = (id) => {
  return apiClient.get(`/api/history/${id}`)
}

export const exportExcel = (tableData) => {
  return apiClient.post('/api/export_excel', { table_data: tableData }, { responseType: 'blob' })
}

// Profile APIs
export const getProfile = (username) => {
  return apiClient.get(`/api/profile/${username}`)
}

export const getMarketTrends = (city = '上海') => {
  return apiClient.get('/api/market/trends', { params: { city } })
}

export const updateProfile = (data) => {
  return apiClient.post('/api/profile/update', data)
}

export const resolveDistrict = (address) => {
  return apiClient.post('/api/address/district', { address })
}

export const getListingAdvice = (data) => {
  return apiClient.post('/api/listing/advice', data)
}

export const generateDescription = (property, style) => {
  return apiClient.post('/api/generate/description', { property, style })
}

export const batchExtractFields = (tableData) => {
  return apiClient.post('/api/batch/extract', { table_data: tableData })
}

export const uploadAvatar = (file, username) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('username', username)
  return apiClient.post('/api/profile/avatar', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export default apiClient
