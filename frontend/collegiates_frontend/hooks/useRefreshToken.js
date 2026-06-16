import axios from "@/axios/axios";
import { setJwt } from "@/lib/slices/jwt";
import { useAppDispatch } from "@/lib/hooks";
import { useEffect } from "react";


const useRefreshToken = () => {
    useEffect(() => {
        axios
            .post("/auth/jwt/refresh", {
                withCredentials: true
            })
            .then((res)=>{
                console.log(res.data);
                dispatch(setJwt(res.data.access));
                console.log("Signed In")
            })
            .catch((err)=>{
            });
    }, []);
}

export default useRefreshToken;