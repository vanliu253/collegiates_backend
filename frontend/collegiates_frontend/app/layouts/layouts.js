import { Provider } from "react-redux";
import { NavBar } from "../components/navbar";
import { MtHeader } from "./headers";
import store from "../store";

function UserLayout({ header = <MtHeader/>, children }) {
    return (
        <Provider store={store}>
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
        </Provider>
    );
}

export { UserLayout };