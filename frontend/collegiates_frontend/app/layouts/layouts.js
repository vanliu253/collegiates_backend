import { clearSuccessMsg } from "@/lib/slices/success";
import { NavBar } from "../components/navbar";
import { MtHeader } from "./headers";
import { useAppDispatch, useAppSelector } from "@/lib/hooks";


function UserLayout({ header = <MtHeader/>, children }) {

    const dispatch = useAppDispatch();
    const success = useAppSelector(state => state.success.message);


    return (
        <>
            <div
                id="bg-component"
                className="bg-tertiary fixed h-screen w-full absolute -top-[0svh] left-0 -z-20"
            />

            <div className="">
                <NavBar/>
            </div>
            <div
                className="antialiased text-dark font-grotesk lg:w-[80%] lg:translate-x-[12.5%] my-2"
            >
                {header}

                <div>{children}</div>
            </div>

            {success ?
                <div className="toast">
                <div className="alert alert-success">
                    <span>{success}</span>
                <button className="btn btn-success btn-circle" onClick={()=>dispatch(clearSuccessMsg())}>X</button>
                </div>
            </div> : <></>}
        </>
    );
}

export { UserLayout };