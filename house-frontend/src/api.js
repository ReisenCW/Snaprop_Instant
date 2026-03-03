import axios from 'axios'
import { API_BASE_URL } from '@/config'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
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

export const getHistory = () => {
  return apiClient.get('/api/history')
}

export const getReportDetail = (id) => {
  return apiClient.get(`/api/history/${id}`)
}

export const exportExcel = (tableData) => {
  return apiClient.post('/api/export_excel', { table_data: tableData }, { responseType: 'blob' })
}

export default apiClient
