import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Send, Sparkles, Clock, Zap, Shield } from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

interface TaskForm {
  input_text: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  metadata: {
    category?: string;
    deadline?: string;
    complexity?: string;
  };
}

const NewTask: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [form, setForm] = useState<TaskForm>({
    input_text: '',
    priority: 'medium',
    metadata: {}
  });
  
  const [charCount, setCharCount] = useState(0);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: async (taskData: TaskForm) => {
      const response = await axios.post('/api/tasks', {
        ...taskData,
        device_info: {
          platform: navigator.platform,
          userAgent: navigator.userAgent,
          screenSize: `${window.innerWidth}x${window.innerHeight}`,
          isMobile: /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
        }
      });
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Task submitted successfully!');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      navigate(`/tasks/${data.task_id}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to submit task');
    }
  });
  
  // Generate suggestions
  useEffect(() => {
    if (form.input_text.length > 10) {
      const words = form.input_text.toLowerCase().split(' ');
      
      const newSuggestions: string[] = [];
      
      if (words.includes('research') || words.includes('find')) {
        newSuggestions.push('Include specific sources or timeframes');
        newSuggestions.push('Add relevant keywords for better results');
      }
      
      if (words.includes('analyze') || words.includes('data')) {
        newSuggestions.push('Consider adding data format preferences');
        newSuggestions.push('Specify the type of analysis needed');
      }
      
      if (words.includes('write') || words.includes('create')) {
        newSuggestions.push('Add tone or style preferences');
        newSuggestions.push('Specify target audience');
      }
      
      setSuggestions(newSuggestions.slice(0, 3));
    } else {
      setSuggestions([]);
    }
  }, [form.input_text]);
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (form.input_text.trim().length < 5) {
      toast.error('Please enter a more detailed task');
      return;
    }
    
    submitMutation.mutate(form);
  };
  
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setCharCount(value.length);
    setForm({ ...form, input_text: value });
  };
  
  const handlePriorityChange = (priority: TaskForm['priority']) => {
    setForm({ ...form, priority });
  };
  
  const exampleTasks = [
    "Research the latest AI developments in 2024 and summarize key trends",
    "Analyze my sales data from last quarter and identify growth opportunities",
    "Create a marketing plan for a new tech product launch",
    "Write a professional email to follow up with potential clients",
    "Compare different cloud hosting providers for a startup"
  ];
  
  const loadExample = (example: string) => {
    setForm({ ...form, input_text: example });
    setCharCount(example.length);
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 pb-20 max-w-2xl mx-auto"
    >
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">New Task</h1>
        <p className="text-gray-600">Describe what you'd like the AI agents to help you with</p>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Task Input */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <label className="block text-lg font-semibold text-gray-900">
              Task Description
            </label>
            <span className={`text-sm ${charCount > 4500 ? 'text-red-500' : 'text-gray-500'}`}>
              {charCount}/5000
            </span>
          </div>
          
          <textarea
            value={form.input_text}
            onChange={handleTextChange}
            placeholder="What would you like me to help you with? Be as specific as possible..."
            className="w-full h-48 p-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:ring-2 focus:ring-blue-200 focus:outline-none resize-none text-gray-900 placeholder-gray-400"
            maxLength={5000}
            disabled={submitMutation.isPending}
          />
          
          {/* Suggestions */}
          {suggestions.length > 0 && (
            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-blue-500" />
                <p className="text-sm font-medium text-blue-800">Suggestions to improve your task:</p>
              </div>
              <ul className="space-y-1">
                {suggestions.map((suggestion, index) => (
                  <li key={index} className="text-sm text-blue-700 flex items-start gap-2">
                    <span className="mt-1">•</span>
                    <span>{suggestion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        
        {/* Priority Selector */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <label className="block text-lg font-semibold text-gray-900 mb-4">
            Priority Level
          </label>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {([
              { level: 'low', label: 'Low', icon: Clock, color: 'bg-gray-100 text-gray-700', activeColor: 'bg-gray-700 text-white' },
              { level: 'medium', label: 'Medium', icon: Zap, color: 'bg-blue-100 text-blue-700', activeColor: 'bg-blue-600 text-white' },
              { level: 'high', label: 'High', icon: Shield, color: 'bg-orange-100 text-orange-700', activeColor: 'bg-orange-600 text-white' },
              { level: 'urgent', label: 'Urgent', icon: Sparkles, color: 'bg-red-100 text-red-700', activeColor: 'bg-red-600 text-white' },
            ] as const).map(({ level, label, icon: Icon, color, activeColor }) => (
              <button
                key={level}
                type="button"
                onClick={() => handlePriorityChange(level)}
                className={`flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all ${
                  form.priority === level 
                    ? `${activeColor} border-transparent` 
                    : `${color} border-gray-200 hover:border-gray-300`
                }`}
              >
                <Icon className="w-6 h-6 mb-2" />
                <span className="font-medium">{label}</span>
              </button>
            ))}
          </div>
          
          <div className="mt-4 text-sm text-gray-500">
            {form.priority === 'low' && 'Task will be processed during low-load periods'}
            {form.priority === 'medium' && 'Standard processing time (recommended for most tasks)'}
            {form.priority === 'high' && 'Expedited processing with higher resource allocation'}
            {form.priority === 'urgent' && 'Immediate processing with maximum resource allocation'}
          </div>
        </div>
        
        {/* Example Tasks */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Need inspiration?</h3>
          <div className="space-y-3">
            {exampleTasks.map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => loadExample(example)}
                className="w-full text-left p-3 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                disabled={submitMutation.isPending}
              >
                <p className="text-gray-700 text-sm">{example}</p>
                <p className="text-blue-500 text-xs mt-1">Click to use this example</p>
              </button>
            ))}
          </div>
        </div>
        
        {/* Submit Button */}
        <div className="sticky bottom-4 z-10">
          <button
            type="submit"
            disabled={submitMutation.isPending || charCount < 5}
            className="w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:transform-none flex items-center justify-center gap-3"
          >
            {submitMutation.isPending ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Processing...
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Submit Task
              </>
            )}
          </button>
          
          <p className="text-center text-xs text-gray-500 mt-3">
            By submitting, you agree to our Terms of Service. Tasks are processed by AI agents.
          </p>
        </div>
      </form>
    </motion.div>
  );
};

export default NewTask;
