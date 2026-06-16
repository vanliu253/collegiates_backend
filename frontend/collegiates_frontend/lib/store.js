import { configureStore } from '@reduxjs/toolkit'
import jwtReducer from './slices/jwt'
import successReducer from './slices/success'


export const makeStore = () => {
  return configureStore({
    reducer: {
      jwt: jwtReducer,
      success: successReducer
    }
  })
}