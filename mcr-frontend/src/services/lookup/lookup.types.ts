export type LookupDto = {
  comu_meeting_id: string;
  secret: string;
};

export type LookupByPasscodeDto = {
  comu_meeting_id: string;
  passcode: string;
};

export type LookupResponseDto = {
  name: string;
};
