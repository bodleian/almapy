from typing import Any, Dict

from httpx import AsyncClient

from almapy.client import Client


class SubClientUserLoans(Client):
    def __init__(
        self,
        session: AsyncClient,
        con_params: Dict[str, Any],
        rate_limit: int = 20,
    ) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/users"

    async def get_loans(self, user_id: str):
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}/loans")
        return response

    async def create_loan(self, user_id: str, item_barcode: str, circ_desk: str, library: str):
        loan = {"circ_desk": {"value": circ_desk}, "library": {"value": library}}
        response = await self.__post_req__(
            f"{self.con_params['api_endpoint']}/{user_id}/loans",
            json=loan,
            params={"item_barcode": item_barcode},
        )
        return response

    async def get_loan(self, user_id: str, loan_id: str):
        response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}")
        return response

    async def renew_loan(self, user_id: str, loan_id: str):
        response = await self.__put_req__(
            f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}",
            params={"op": "renew"},
        )
        return response

    async def change_loan_due_date(self, user_id: str, loan_id: str, due_date: str):
        loan = {"due_date": due_date}
        response = await self.__put_req__(f"{self.con_params['api_endpoint']}/{user_id}/loans/{loan_id}", json=loan)
        return response


class SubClientUsers(Client):
    def __init__(self, session: AsyncClient, con_params: Dict[str, Any], rate_limit: int = 20) -> None:
        super().__init__(session, con_params, rate_limit)
        self.con_params = con_params.copy()
        self.con_params["api_endpoint"] = "/almaws/v1/users"
        self.loans = SubClientUserLoans(session, self.con_params, rate_limit)

    async def get_user(self, user_id: str, xml: bool = False):
        if not xml:
            response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}")
            return response
        else:
            response = await self.__get_req__(f"{self.con_params['api_endpoint']}/{user_id}", xml=True)
            return response

    async def update_user(self, user_id: str, body: str):
        response = await self.__put_req__(f"{self.con_params['api_endpoint']}/{user_id}", body, xml=True)
        return response
