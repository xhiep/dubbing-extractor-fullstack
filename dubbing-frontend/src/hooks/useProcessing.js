import { useMutation, useQuery } from '@tanstack/react-query'
import { processAPI, previewAPI } from '../api/client'
import useAppStore from '../store/appStore'
import toast from 'react-hot-toast'

export const useProcessing = () => {
  const { processingOptions, setTaskId, setStatus, addLog, reset } = useAppStore()

  const startMutation = useMutation({
    mutationFn: () => processAPI.start(processingOptions),
    onSuccess: (data) => {
      setTaskId(data.task_id)
      setStatus(data.status)
      addLog('info', `Task started: ${data.task_id}`)
      toast.success('Processing started')
    },
    onError: (error) => {
      addLog('error', error.message)
      toast.error(error.message)
    },
  })

  const cancelMutation = useMutation({
    mutationFn: (taskId) => processAPI.cancel(taskId),
    onSuccess: () => {
      setStatus('failed')
      addLog('warning', 'Task cancelled by user')
      toast.success('Task cancelled')
    },
    onError: (error) => {
      addLog('error', error.message)
      toast.error(error.message)
    },
  })

  return {
    start: startMutation.mutate,
    cancel: cancelMutation.mutate,
    isStarting: startMutation.isPending,
    isCancelling: cancelMutation.isPending,
    reset,
  }
}

export const usePreview = (source) => {
  return useQuery({
    queryKey: ['preview', source],
    queryFn: () => previewAPI.getInfo(source),
    enabled: !!source && source.length > 0,
    retry: false,
  })
}

export const useStepProcessing = () => {
  const { setTaskId, setStatus, addLog } = useAppStore()

  const runStepMutation = useMutation({
    mutationFn: ({ stepNum, taskId, stepData }) =>
      processAPI.runStep(stepNum, { task_id: taskId, step_data: stepData }),
    onSuccess: (data, variables) => {
      setTaskId(data.task_id)
      setStatus(data.status)
      addLog('info', `Step ${variables.stepNum} started`)
      toast.success(`Step ${variables.stepNum} started`)
    },
    onError: (error) => {
      addLog('error', error.message)
      toast.error(error.message)
    },
  })

  return {
    runStep: runStepMutation.mutate,
    isRunning: runStepMutation.isPending,
  }
}
