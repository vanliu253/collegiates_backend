import { configureStore } from '@reduxjs/toolkit'
import jwtReducer from './slices/jwt'


export default configureStore({
  reducer: {
    jwt: jwtReducer
  }
})