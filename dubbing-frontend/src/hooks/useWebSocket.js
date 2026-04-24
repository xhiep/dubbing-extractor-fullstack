import { useEffect, useRef, useState } from 'react'
import { io } from 'socket.io-client'
import useAppStore from '../store/appStore'

const useWebSocket = () => {
  const socketRef = useRef(null)
  const [connected, setConnected] = useState(false)

  const { taskId, setProgress, addLog, setStatus, setOutputs } = useAppStore()

  useEffect(() => {
    // Create socket connection
    const socket = io('http://localhost:8000', {
      path: '/ws/socket.io',
      transports: ['websocket', 'polling'],
    })

    socketRef.current = socket

    // Connection events
    socket.on('connect', () => {
      console.log('WebSocket connected')
      setConnected(true)
      addLog('info', 'Connected to server')
    })

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setConnected(false)
      addLog('warning', 'Disconnected from server')
    })

    socket.on('connected', (data) => {
      console.log('Server message:', data.message)
    })

    // Task events
    socket.on('progress', (data) => {
      console.log('Progress:', data)
      setProgress(data.step, data.progress, data.message)
    })

    socket.on('log', (data) => {
      console.log('Log:', data)
      addLog(data.level, data.message)
    })

    socket.on('completed', (data) => {
      console.log('Completed:', data)
      setStatus('completed')
      setOutputs(data.outputs)
      addLog('info', 'Processing completed successfully')
    })

    socket.on('error', (data) => {
      console.error('Error:', data)
      setStatus('failed')
      addLog('error', `Error: ${data.error}`)
    })

    // Cleanup
    return () => {
      socket.disconnect()
    }
  }, [])

  // Subscribe to task updates when taskId changes
  useEffect(() => {
    if (taskId && socketRef.current && connected) {
      console.log('Subscribing to task:', taskId)
      socketRef.current.emit('subscribe', { task_id: taskId })

      socketRef.current.once('subscribed', (data) => {
        console.log('Subscribed to task:', data.task_id)
        addLog('info', `Subscribed to task ${data.task_id}`)
      })
    }
  }, [taskId, connected])

  return {
    socket: socketRef.current,
    connected,
  }
}

export default useWebSocket
