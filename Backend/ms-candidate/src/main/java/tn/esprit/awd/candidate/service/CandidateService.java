package tn.esprit.awd.candidate.service;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tn.esprit.awd.candidate.dto.CandidateRequest;
import tn.esprit.awd.candidate.dto.CandidateResponse;
import tn.esprit.awd.candidate.entity.Address;
import tn.esprit.awd.candidate.entity.Candidate;
import tn.esprit.awd.candidate.exception.ConflictException;
import tn.esprit.awd.candidate.exception.ResourceNotFoundException;
import tn.esprit.awd.candidate.mapper.CandidateMapper;
import tn.esprit.awd.candidate.repository.CandidateRepository;

import java.util.List;

@Service
@Transactional
public class CandidateService {

    private final CandidateRepository candidateRepository;
    private final AddressService addressService;

    public CandidateService(CandidateRepository candidateRepository, AddressService addressService) {
        this.candidateRepository = candidateRepository;
        this.addressService = addressService;
    }

    @Transactional(readOnly = true)
    public List<CandidateResponse> findAll() {
        return candidateRepository.findAll().stream().map(CandidateMapper::toResponse).toList();
    }

    @Transactional(readOnly = true)
    public CandidateResponse findById(Long id) {
        return CandidateMapper.toResponse(getCandidate(id));
    }

    public CandidateResponse create(CandidateRequest request) {
        if (candidateRepository.existsByEmailIgnoreCase(request.email())) {
            throw new ConflictException("A candidate with email " + request.email() + " already exists");
        }
        Candidate saved = candidateRepository.save(CandidateMapper.toEntity(request));
        return CandidateMapper.toResponse(saved);
    }

    public CandidateResponse update(Long id, CandidateRequest request) {
        Candidate candidate = getCandidate(id);
        if (candidateRepository.existsByEmailIgnoreCaseAndIdNot(request.email(), id)) {
            throw new ConflictException("A candidate with email " + request.email() + " already exists");
        }
        candidate.setFirstname(request.firstname());
        candidate.setLastname(request.lastname());
        candidate.setEmail(request.email());

        if (request.address() != null) {
            if (candidate.getAddress() != null) {
                CandidateMapper.updateEntity(candidate.getAddress(), request.address());
            } else {
                candidate.setAddress(CandidateMapper.toEntity(request.address()));
            }
        }
        return CandidateMapper.toResponse(candidateRepository.saveAndFlush(candidate));
    }

    public void delete(Long id) {
        Candidate candidate = getCandidate(id);
        candidateRepository.delete(candidate);
    }

    public CandidateResponse assignAddress(Long candidateId, Long addressId) {
        Candidate candidate = getCandidate(candidateId);
        Address address = addressService.getAddress(addressId);

        if (address.getCandidate() != null && !address.getCandidate().getId().equals(candidateId)) {
            throw new ConflictException("Address " + addressId + " is already assigned to candidate "
                    + address.getCandidate().getId());
        }
        candidate.setAddress(address);
        return CandidateMapper.toResponse(candidateRepository.saveAndFlush(candidate));
    }

    public CandidateResponse removeAddress(Long candidateId) {
        Candidate candidate = getCandidate(candidateId);
        candidate.setAddress(null);
        return CandidateMapper.toResponse(candidateRepository.saveAndFlush(candidate));
    }

    public Candidate getCandidate(Long id) {
        return candidateRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Candidate", id));
    }
}
