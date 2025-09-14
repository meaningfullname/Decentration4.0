"use client"
/* eslint-disable @typescript-eslint/no-explicit-any */
import React, { useState,useEffect } from 'react'
import { motion,AnimatePresence } from 'framer-motion'
import { Card,CardContent,CardDescription,CardHeader,CardTitle } from "../src/ui/card"
import { Button } from "../src/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../src/ui/table"
import { Progress } from "../src/ui/progress"
import { Badge } from "../src/ui/badge"
import { Toaster,toast } from 'sonner'
import { Loader2,TrendingUp,CreditCard,Banknote,PiggyBank,LineChart,Coins,DollarSign,Briefcase } from 'lucide-react'
import Header from '../src/common/Header'
import axios from 'axios'
import Link from 'next/link'

interface Client{
  client_code: number
  name: string
  product: string
  status: string
  city: string
}

interface Recommendation{
  product: string
  message: string
  confidence: number
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const containerVariants = {
  hidden: {
    opacity: 0,
  },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    }
  }
}
const productIcons: {[key:string]:any} = {
  'Карта для путешествий': TrendingUp,
  'Премиальная карта': CreditCard,
  'Кредитная карта': Banknote,
  'Депозит накопительный': PiggyBank,
  'Депозит сберегательный': PiggyBank,
  'Инвестиции': LineChart,
  'Золотые слитки': Coins,
  'Обмен валют': DollarSign,
  'Кредит наличными': Briefcase,
}

export default function Home() {
  const [clients, setClients] = useState<Client[]>([])
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isFetchingClients, setIsFetchingClients] = useState(true)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<Recommendation[]>([])
  const [topRecommendation, setTopRecommendation] = useState<Recommendation | null>(null)

  useEffect(()=>{
    fetchClients()
  },[])

  const fetchClients = async()=>{
    try{
      setIsFetchingClients(true)
      const resp = await axios.get(`${API_URL}/api/clients`)
      console.log('clients', resp.data);

      setClients(resp.data.clients)
    }
    catch(error:any){
      console.error('Ошибка загрузки клиентов',error);
      toast.error('Не удалось загрузить список клиентов')
    }
    finally{
      setIsFetchingClients(false)
    }
  }
  const runDiagnostics = async()=>{
    if(!selectedClient){
      toast.error('Выберите клиента для диагностики')
      return
    }

    setIsLoading(true)
    setProgress(0)
    setResults([])
    setTopRecommendation(null)

    const loadingToast = toast.loading('Запуск диагностики...')
    const interval = setInterval(() => {
      setProgress((prev)=>{
        if(prev >= 90){
          clearInterval(interval)
          return 90
        }
        return prev + 10
      })
    }, 200)

    try{
      console.log(selectedClient.client_code);
      const resp = await axios.post(`${API_URL}/api/diagnose`, {
        client_code: selectedClient.client_code,
      })
      console.log('diagnose response', resp.data);

      if(resp.status !== 200){
        throw new Error('Ошибка диагностики')
      }
      setProgress(100)
      setTimeout(()=>{
        setResults(resp.data.recommendations)
        if(resp.data.recommendations && resp.data.recommendations.length > 0){
          const topRec = resp.data.recommendations.reduce((prev: Recommendation,current: Recommendation)=> prev.confidence > current.confidence ? prev : current)
          setTopRecommendation(topRec)
          toast.success(topRec.product,{
            description: (
              <div>
                <Link className='cursor-pointer' href='https://www.bcc.kz/personal/loans/cash-credit/?utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw_big_cities&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&gad_source=1&gad_campaignid=22341016002&gbraid=0AAAAAqIqjI8v1i_Pj4A8Lu0SDnGgj4uLQ&gclid=CjwKCAjwz5nGBhBBEiwA-W6XRD5f3sc6c4sTBavj849DyqoU44crm7w48LIaidZczJ3NfMLr5YSTmBoC6T0QAvD_BwE'>{topRec.message}</Link>
                <p className="text-xs mt-2">Точность: {Math.floor(topRec.confidence)}%</p>
              </div>
            ),
          })
        }
        
        setIsLoading(false)
        clearInterval(interval)

        toast.dismiss(loadingToast)
        toast.success('Диагностика завершена!', { description: `Найдено ${resp.data.recommendations.length} рекомендаций для ${resp.data.client_name}` })
      },500)

    }
    catch(error:any){
      console.error('Ошибка диагностики',error)
      toast.dismiss(loadingToast)
      toast.error('Произошла ошибка при диагностике')
      setIsLoading(false)
    }
  }
  const getStatusVariant = (status:string)=>{
    const statusMap: { [key: string]: "default" | "secondary" | "destructive" | "outline" } = {
      'Зарплатный клиент':'default',
      'Премиальный клиент':'default',
      'Студент':'secondary',
      'Стандартный клиент':'outline',
    }
    return statusMap[status] || 'outline'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 p-6">
      <Toaster richColors />
      <div className="max-w-6xl mx-auto">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
          <Header />
          <p className="text-slate-600 mb-8">Выберите клиента для персональной диагностики финансового профиля</p>
        </motion.div>
        <motion.div variants={containerVariants} initial="hidden" animate="visible">
          <Card className="mb-8">
            <CardHeader>
              <CardTitle>Список клиентов</CardTitle>
              <CardDescription>Выберите клиента из таблицы для запуска диагностики</CardDescription>
            </CardHeader>
            <CardContent>
              {isFetchingClients ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Код клиента</TableHead>
                      <TableHead>Имя</TableHead>
                      <TableHead>Продукт</TableHead>
                      <TableHead>Статус</TableHead>
                      <TableHead>Город</TableHead>
                      <TableHead>Действия</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {clients.map((client, index) => (
                      <motion.tr key={index} variants={{
                        hidden:{
                          y:20,
                          opacity:0,
                        },
                        visible:{
                          y:0,
                          opacity:1,
                          transition:{
                            type:"spring",
                            stiffness: 120,
                          }
                        },
                      }} className={selectedClient?.client_code === client.client_code ? "bg-slate-50" : ""}>
                        <TableCell>{client.client_code}</TableCell>
                        <TableCell className="font-medium">{client.name}</TableCell>
                        <TableCell>{client.product}</TableCell>
                        <TableCell>
                          <Badge variant={getStatusVariant(client.status)}>{client.status}</Badge>
                        </TableCell>
                        <TableCell>{client.city}</TableCell>
                        <TableCell>
                          <Button onClick={()=>{setSelectedClient(client)}} variant={selectedClient?.client_code == client.client_code ? "default" : "outline"} size="sm">{selectedClient?.client_code == client.client_code ? "Выбран" : "Выбрать"}</Button>
                        </TableCell>
                      </motion.tr>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </motion.div>
        <AnimatePresence>
          {selectedClient && (
            <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 40 }} transition={{ duration: 0.3 }}>
              <Card>
                <CardHeader>
                  <CardTitle>Диагностика клиента</CardTitle>
                  <CardDescription> Анализ финансового поведения {selectedClient.name} для персональных рекомендаций </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 mb-6">
                    <div className="flex-1">
                      <h3 className="font-semibold">{selectedClient.name}</h3>
                      <p className="text-sm text-slate-600">{selectedClient.client_code} • {selectedClient.city}</p>
                    </div>
                    <Button onClick={runDiagnostics} disabled={isLoading}>{isLoading ? "Запущена диагностика..." : "Запустить диагностику"}</Button>
                  </div>
                  <AnimatePresence>
                    {isLoading && (
                      <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="space-y-4 mt-6 overflow-hidden">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">Анализ данных</span>
                          <span className="text-sm text-slate-500">{progress}%</span>
                        </div>
                        <Progress value={progress} className="h-2" />
                        <div className="text-center py-8">
                          <motion.div animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }} transition={{ repeat: Infinity, duration: 1.5 }} className="relative inline-flex">
                            <div className="relative rounded-full h-16 w-16 bg-gradient-to-r from-blue-500 to-indigo-500 flex items-center justify-center">
                              <Loader2 className="w-8 h-8 text-white animate-spin" />
                            </div>
                          </motion.div>
                          <p className="text-sm text-slate-500 mt-4">Анализируем финансовое поведение клиента...</p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <AnimatePresence>
                    {topRecommendation && (
                      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="mt-6 mb-6">
                        <h3 className="font-semibold text-lg mb-4">Лучшая рекомендация:</h3>
                        <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="p-4 rounded-lg border-2 border-blue-200 shadow-md bg-gradient-to-r from-blue-50 to-indigo-50 flex items-start gap-3">
                          <div className="p-2 rounded-full bg-blue-100">{React.createElement(productIcons[topRecommendation.product] || CreditCard, { className: "w-5 h-5 text-blue-600" })}</div>
                          <div className="flex-1">
                            <div className="flex justify-between items-start mb-2">
                              <h4 className="font-semibold text-blue-800">{topRecommendation.product}</h4>
                              <Badge className={`${topRecommendation.confidence >= 90 ? 'bg-green-500' : topRecommendation.confidence >= 80 ? 'bg-blue-500' : 'bg-amber-500'}`}>{Math.floor(topRecommendation.confidence)}% уверенность</Badge>
                            </div>
                            <Link href='https://www.bcc.kz/personal/loans/cash-credit/?utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw_big_cities&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&gad_source=1&gad_campaignid=22341016002&gbraid=0AAAAAqIqjI8v1i_Pj4A8Lu0SDnGgj4uLQ&gclid=CjwKCAjwz5nGBhBBEiwA-W6XRD5f3sc6c4sTBavj849DyqoU44crm7w48LIaidZczJ3NfMLr5YSTmBoC6T0QAvD_BwE' className="text-sm text-slate-700 cursor-pointer">{topRecommendation.message}</Link>
                          </div>
                        </motion.div>
                      </motion.div>
                    )}
                  </AnimatePresence> 
                  <AnimatePresence>
                    {results.length > 0 && !isLoading && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-6 space-y-4">
                        <h3 className="font-semibold text-lg mb-4">Все рекомендации:</h3>
                        {results.map((rec,index)=>{
                          const Icon = productIcons[rec.product] || CreditCard
                          return (
                            <motion.div key={index} initial={{opacity: 0,y: 20}} animate={{opacity: 1,y:0}} transition={{delay: index * 0.1}} className="p-4 rounded-lg border shadow-sm flex items-start gap-3 bg-white">
                              <div className={`p-2 rounded-full ${rec.confidence > 90 ? 'bg-green-100' : rec.confidence > 80 ? 'bg-blue-100' : 'bg-slate-100'}`}>
                                <Icon className="w-5 h-5 text-slate-600" />
                              </div>
                              <div>
                                <h4 className="font-semibold">{rec.product}</h4>
                                <Link href='https://www.bcc.kz/personal/loans/cash-credit/?utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw_big_cities&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&utm_source=google&utm_medium=cpc&utm_campaign=bcc_kredit_google_search_kw&utm_content={{adset.name}}&utm_term={{site_source_name}}{}&gad_source=1&gad_campaignid=22341016002&gbraid=0AAAAAqIqjI8v1i_Pj4A8Lu0SDnGgj4uLQ&gclid=CjwKCAjwz5nGBhBBEiwA-W6XRD5f3sc6c4sTBavj849DyqoU44crm7w48LIaidZczJ3NfMLr5YSTmBoC6T0QAvD_BwE' className="text-sm text-slate-600 cursor-pointer">{rec.message}</Link>
                                <p className="text-xs mt-1">Точность: {Math.floor(rec.confidence)}%</p>
                              </div>
                            </motion.div>
                          )
                        })}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}